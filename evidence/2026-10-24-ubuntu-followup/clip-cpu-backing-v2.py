"""Experimental, instance-scoped GGUF CLIP offload with original CPU storage.

No LoRA, hooks or weight/object patches except core CLIP's FP32 compute policy are accepted. This does not change the
stock GGUF class, core unload implementation, or the older MODEL candidate.
"""
import logging

import torch

TAG = '[CLIP-CPU-BACKING]'


def _check_patches(patcher):
    objects = getattr(patcher, 'object_patches', {})
    core_compute_policy = not objects or (
        set(objects) == {'manual_cast_dtype'} and objects['manual_cast_dtype'] == torch.float32)
    if not core_compute_policy or any(getattr(patcher, name, None) for name in
           ('patches', 'hook_patches', 'weight_wrapper_patches')):
        raise ValueError('GGUF CLIP CPU backing experiment does not support LoRA, hooks or patches')


def _specialize(base_class):
    class GgufClipCpuBackingPatcher(base_class):
        _lab_clip_cpu_restore = True

        def patch_model(self, *args, **kwargs):
            _check_patches(self)
            return super().patch_model(*args, **kwargs)

        def clone(self, *args, **kwargs):
            scoped_class = type(self)
            result = super().clone(*args, **kwargs)
            # The installed GGUF clone explicitly resets its result to the
            # stock class. Keep this instance policy on descendant CLIP clones.
            result.__class__ = scoped_class
            return result

        def unpatch_model(self, device_to=None, unpatch_weights=True):
            if device_to is None or torch.device(device_to).type != 'cpu' or not unpatch_weights:
                return super().unpatch_model(device_to=device_to, unpatch_weights=unpatch_weights)
            _check_patches(self)
            cache = self.model._lab_clip_cpu_backing
            if set(dict(self.model.named_parameters())) != set(cache):
                raise RuntimeError('CLIP parameter structure changed; CPU restore refused')
            import comfy.utils
            with torch.no_grad():
                # Preserve installed cleanup of pins/backups/hooks, but avoid its
                # full new CPU allocation. Restore parameters before moving buffers.
                result = super().unpatch_model(device_to=None, unpatch_weights=True)
                for name, (base, tensor_class, metadata) in cache.items():
                    values = dict(metadata) if metadata else None
                    if values is not None:
                        values['patches'] = []
                    value = tensor_class(base, **values) if tensor_class else base
                    comfy.utils.set_attr_param(self.model, name, value)
                self.model.to(device_to)
                self.model.device = device_to
            logging.warning('%s restored %d original CPU parameter storages', TAG, len(cache))
            return result

    return GgufClipCpuBackingPatcher


class RetainGgufClipCpuBacking:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'clip': ('CLIP',)}}

    RETURN_TYPES = ('CLIP',)
    FUNCTION = 'enable'
    CATEGORY = 'repair/experimental'

    def enable(self, clip):
        patcher = clip.patcher
        _check_patches(patcher)
        if getattr(type(patcher), '_lab_clip_cpu_restore', False):
            return (clip.clone(),)
        if type(patcher).__name__ != 'GGUFModelPatcher':
            raise ValueError('Only the recorded GGUFModelPatcher CLIP is supported')
        cache = {}
        for name, parameter in patcher.model.named_parameters():
            if parameter.device.type != 'cpu' or parameter.requires_grad:
                raise ValueError('Enable before the first GPU load, on inference-only CPU weights')
            if type(parameter).__name__ == 'GGMLTensor':
                # Plain Tensor.detach removes a view's _base reference to a
                # Parameter whose .data may later move to GPU, without copying.
                base = parameter.as_subclass(torch.Tensor).detach()
                metadata = {'tensor_type': parameter.tensor_type,
                            'tensor_shape': parameter.tensor_shape, 'patches': []}
                if parameter.patches:
                    raise ValueError('GGUF CLIP CPU backing does not support existing LoRA patches')
                tensor_class = type(parameter)
            elif type(parameter) in (torch.Tensor, torch.nn.Parameter):
                base, tensor_class, metadata = parameter.detach(), None, None
            else:
                raise ValueError('Unsupported parameter subclass: ' + type(parameter).__name__)
            cache[name] = (base, tensor_class, metadata)
        if not cache:
            raise ValueError('No CLIP parameters found')
        wrapped = clip.clone()
        wrapped.patcher.__class__ = _specialize(type(patcher))
        # This policy is a new root. Later clones must fall back to this scoped
        # root rather than the loader's stock patcher during weakref cleanup.
        wrapped.patcher.parent = None
        wrapped.patcher.model._lab_clip_cpu_backing = cache
        logging.warning('%s retained %d CPU storages, %d raw bytes; no dense copy',
                        TAG, len(cache), sum(base.numel() * base.element_size() for base, _, _ in cache.values()))
        return (wrapped,)


NODE_CLASS_MAPPINGS = {'RetainGgufClipCpuBacking': RetainGgufClipCpuBacking}
NODE_DISPLAY_NAME_MAPPINGS = {'RetainGgufClipCpuBacking': 'Retain original GGUF CLIP CPU storage (experimental)'}
