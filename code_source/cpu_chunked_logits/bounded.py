"""Bound CPU Qwen INT8 vocabulary projection without changing its weights."""
from dataclasses import replace
import logging

import torch
from comfy_kitchen.tensor import QuantizedTensor

CHUNK_ROWS = 2048
_reported = set()


def chunked_logits(head, x, devices=("cpu",)):
    weight = head.weight
    if (torch.is_grad_enabled() or x.device.type not in devices or
        not isinstance(weight, QuantizedTensor) or weight.device.type not in {"cpu", x.device.type} or
        weight._layout_cls != "TensorWiseINT8Layout" or head.bias is not None or
        getattr(head, "pre_quant_scale", None) is not None or
        getattr(head, "weight_function", []) or getattr(head, "weight_lowvram_function", None) is not None):
        return None
    params = weight.params
    if getattr(params, "transposed", False) or not getattr(params, "is_weight", True):
        return None
    qdata = weight._qdata
    if qdata.ndim != 2 or tuple(qdata.shape) != tuple(weight.shape):
        return None
    rows = qdata.shape[0]
    scale = params.scale
    scalar = scale.numel() == 1
    if not scalar and not (scale.shape[0] == rows and scale.numel() == rows):
        return None
    # Keep the native quantized path when it is actually usable.
    if weight.dtype == x.dtype and not getattr(head, "_full_precision_mm", False):
        return None
    input = x[:, -1:]
    output = torch.empty((*input.shape[:-1], rows), device=input.device, dtype=input.dtype)
    for start in range(0, rows, CHUNK_ROWS):
        end = min(start + CHUNK_ROWS, rows)
        local_scale = scale if scalar else scale[start:end]
        local = replace(params, orig_dtype=input.dtype, orig_shape=(end - start, qdata.shape[1]),
                        scale=local_scale.to(input.device))
        dense = weight.layout_cls.dequantize(qdata[start:end].to(input.device), local)
        output[..., start:end] = torch.nn.functional.linear(input, dense)
        del dense
    shape = tuple(qdata.shape)
    if shape not in _reported:
        logging.info("AMD ComfyUI Guide: %s INT8 Qwen logits %s use at most %d vocabulary rows per dequantization", input.device, shape, CHUNK_ROWS)
        _reported.add(shape)
    return output


def install(include_cuda=False):
    from comfy.text_encoders.llama import BaseQwen3
    if getattr(BaseQwen3.logits, "_barely_chunked_cpu", False):
        return
    original = BaseQwen3.logits

    def logits(self, x):
        if self.model.config.lm_head:
            result = chunked_logits(self.model.lm_head, x, devices=("cpu", "cuda") if include_cuda else ("cpu",))
            if result is not None:
                return result
        return original(self, x)

    logits._barely_chunked_cpu = True
    BaseQwen3.logits = logits
    logging.info("AMD ComfyUI Guide: opt-in bounded Qwen INT8 vocabulary projection enabled; HIP/CUDA=%s", include_cuda)
