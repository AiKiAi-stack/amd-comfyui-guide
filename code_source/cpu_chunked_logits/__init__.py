"""Opt-in workaround for CPU Qwen caption vocabulary-projection memory spikes."""
import os

NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

if os.environ.get("BARELY_COMFY_CHUNKED_CPU_LOGITS") == "1":
    from .bounded import install
    install(include_cuda=os.environ.get("BARELY_COMFY_CHUNKED_GPU_LOGITS") == "1")
