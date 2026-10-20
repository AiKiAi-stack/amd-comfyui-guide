"""Opt-in workaround for HIP INT8 GEMM failures on this RX 6650 XT.

Enable only in a trial process with COMFY_GFX1032_INT8_FALLBACK=1.
Uses ComfyUI's existing emulated quantized formats; does not modify weights.
"""

import logging
import os

import torch

import comfy.model_management as model_management


NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

if os.environ.get("COMFY_GFX1032_INT8_FALLBACK") == "1":
    if torch.version.hip and torch.cuda.is_available():
        properties = torch.cuda.get_device_properties(torch.cuda.current_device())
        architecture = getattr(properties, "gcnArchName", "").split(":", 1)[0]
        if architecture == "gfx1032":
            original_supports_int8 = model_management.supports_int8_compute

            def supports_int8_compute(device=None):
                if device is None or torch.device(device).type == "cuda":
                    return False
                return original_supports_int8(device)

            model_management.supports_int8_compute = supports_int8_compute
            logging.warning(
                "gfx1032 trial: INT8 GEMM disabled; using ComfyUI's dequantized matmul fallback."
            )
        else:
            logging.warning("gfx1032 INT8 fallback requested but GPU is %s; not applied.", architecture)
