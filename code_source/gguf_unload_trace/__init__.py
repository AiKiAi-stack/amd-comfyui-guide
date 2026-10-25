"""Explicit diagnostic node: identify the last real GGUF transfer before native exit."""
import functools
import logging
import weakref
import os


def available_commit():
    if os.name != 'nt':
        return None
    import ctypes
    import struct
    memory = ctypes.create_string_buffer(64)
    struct.pack_into('I', memory, 0, 64)
    if ctypes.windll.kernel32.GlobalMemoryStatusEx(memory):
        return struct.unpack_from('Q', memory, 32)[0]
    return None


class TraceRepairGgufUnloads:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'model': ('MODEL',)}}

    RETURN_TYPES = ('MODEL',)
    FUNCTION = 'enable'
    CATEGORY = 'repair/diagnostics'

    def enable(self, model):
        patcher_cls = type(model)
        if patcher_cls.__name__ != 'GGUFModelPatcher':
            raise ValueError('This diagnostic requires the actual GGUFModelPatcher')
        tensor_classes = {type(p) for p in model.model.parameters() if type(p).__name__ == 'GGMLTensor'}
        if not tensor_classes:
            raise ValueError('No real GGMLTensor weights found')
        for tensor_cls in tensor_classes:
            if getattr(tensor_cls.to, '_barely_unload_trace', False):
                continue
            original_to = tensor_cls.to

            def make_to(original):
                @functools.wraps(original)
                def traced(tensor, *args, **kwargs):
                    name = getattr(tensor, '_barely_unload_parameter', None)
                    if name is not None:
                        logging.warning('GGUF_UNLOAD_BEFORE name=%s device=%s dtype=%s raw_size=%s commit_available=%s args=%r kwargs=%r',
                                        name, tensor.device, tensor.dtype, tuple(tensor.size()), available_commit(), args, kwargs)
                    result = original(tensor, *args, **kwargs)
                    if name is not None:
                        logging.warning('GGUF_UNLOAD_AFTER name=%s device=%s', name, result.device)
                    return result
                traced._barely_unload_trace = True
                return traced
            tensor_cls.to = make_to(original_to)
        if not getattr(patcher_cls.unpatch_model, '_barely_unload_trace', False):
            original_unpatch = patcher_cls.unpatch_model

            @functools.wraps(original_unpatch)
            def traced_unpatch(patcher, *args, **kwargs):
                tagged = []
                for name, parameter in patcher.model.named_parameters():
                    if type(parameter).__name__ == 'GGMLTensor':
                        parameter._barely_unload_parameter = name
                        tagged.append(weakref.ref(parameter))
                try:
                    return original_unpatch(patcher, *args, **kwargs)
                finally:
                    for reference in tagged:
                        parameter = reference()
                        if parameter is not None and hasattr(parameter, '_barely_unload_parameter'):
                            del parameter._barely_unload_parameter
            traced_unpatch._barely_unload_trace = True
            patcher_cls.unpatch_model = traced_unpatch
        return (model,)


NODE_CLASS_MAPPINGS = {'TraceRepairGgufUnloads': TraceRepairGgufUnloads}
NODE_DISPLAY_NAME_MAPPINGS = {'TraceRepairGgufUnloads': 'Trace real GGUF unload (diagnostic)'}
