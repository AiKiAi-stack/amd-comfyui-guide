"""Opt-in GGUF offload using retained original CPU storage instead of a new full copy."""
import functools
import logging

import torch


class RepairGgufMmapOffload:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'model': ('MODEL',)}}

    RETURN_TYPES = ('MODEL',)
    FUNCTION = 'enable'
    CATEGORY = 'repair/experimental'

    def enable(self, model):
        cls = type(model)
        if cls.__name__ != 'GGUFModelPatcher':
            raise ValueError('Only GGUFModelPatcher is supported')
        if not hasattr(model.model, '_barely_cpu_backing'):
            cache = {}
            for name, parameter in model.model.named_parameters():
                if parameter.device.type != 'cpu' or parameter.requires_grad:
                    raise ValueError('Enable before the first GPU load, on inference-only CPU weights')
                if type(parameter).__name__ == 'GGMLTensor':
                    # GGMLTensor.detach/clone return self. A base view keeps the CPU
                    # storage alive independently when Parameter.data later moves.
                    base = parameter.as_subclass(torch.Tensor)
                    metadata = {'tensor_type': parameter.tensor_type,
                                'tensor_shape': parameter.tensor_shape, 'patches': []}
                    tensor_cls = type(parameter)
                elif type(parameter) in {torch.Tensor, torch.nn.Parameter}:
                    base, metadata, tensor_cls = parameter.detach(), None, None
                else:
                    raise ValueError('Unsupported tensor subclass: ' + type(parameter).__name__)
                cache[name] = (base, tensor_cls, metadata)
            if not cache:
                raise ValueError('No weights found')
            model.model._barely_cpu_backing = cache
            logging.warning('GGUF mmap offload: retained %d CPU backing tensors, %d raw bytes; no dense clone',
                            len(cache), sum(x[0].numel() * x[0].element_size() for x in cache.values()))
        if not getattr(cls.unpatch_model, '_barely_mmap_offload', False):
            original = cls.unpatch_model

            @functools.wraps(original)
            def unpatch(patcher, device_to=None, unpatch_weights=True):
                cache = getattr(patcher.model, '_barely_cpu_backing', None)
                if not cache or device_to is None or torch.device(device_to).type != 'cpu' or not unpatch_weights:
                    return original(patcher, device_to=device_to, unpatch_weights=unpatch_weights)
                import comfy.utils
                with torch.inference_mode():
                    # Let the installed implementation remove LoRA patches, hooks,
                    # pins and backups, but skip its allocating model.to(cpu).
                    result = original(patcher, device_to=None, unpatch_weights=True)
                    if set(dict(patcher.model.named_parameters())) != set(cache):
                        raise RuntimeError('Model parameter structure changed; CPU backing restore refused')
                    for name, (base, tensor_cls, metadata) in cache.items():
                        value = tensor_cls(base, **metadata) if tensor_cls else base
                        comfy.utils.set_attr_param(patcher.model, name, value)
                    # Parameters already use their original CPU storage. This moves
                    # any small runtime buffers without copying the whole GGUF back.
                    patcher.model.to(device_to)
                    patcher.model.device = device_to
                    logging.warning('GGUF mmap offload: restored %d original CPU parameter storages', len(cache))
                    return result
            unpatch._barely_mmap_offload = True
            cls.unpatch_model = unpatch
        return (model,)


NODE_CLASS_MAPPINGS = {'RepairGgufMmapOffload': RepairGgufMmapOffload}
NODE_DISPLAY_NAME_MAPPINGS = {'RepairGgufMmapOffload': 'Retain GGUF CPU backing for offload (experimental)'}
