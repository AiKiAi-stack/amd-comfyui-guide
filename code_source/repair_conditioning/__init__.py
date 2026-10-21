"""Persist exact conditioning between isolated encoder and denoising processes."""
import hashlib
import json
from pathlib import Path
import re
import uuid

import folder_paths
import torch
from safetensors import safe_open
from safetensors.torch import load_file, save_file


def pack(value, tensors):
    if isinstance(value, torch.Tensor):
        if hasattr(value, "_qdata"):
            raise TypeError("Expected dense conditioning, received quantized model storage")
        key = f"tensor_{len(tensors)}"
        # Positive/negative conditions can share storage; safetensors requires
        # independent buffers for separate names.
        tensors[key] = value.detach().to("cpu").contiguous().clone()
        return ["tensor", key]
    if isinstance(value, dict):
        return ["dict", [[pack(k, tensors), pack(v, tensors)] for k, v in value.items()]]
    if isinstance(value, tuple):
        return ["tuple", [pack(v, tensors) for v in value]]
    if isinstance(value, list):
        return ["list", [pack(v, tensors) for v in value]]
    if value is None or isinstance(value, (str, int, float, bool)):
        return ["literal", value]
    raise TypeError(f"Unsupported conditioning metadata type: {type(value).__name__}")


def unpack(value, tensors):
    kind, item = value
    if kind == "tensor":
        return tensors[item]
    if kind == "dict":
        return {unpack(k, tensors): unpack(v, tensors) for k, v in item}
    if kind in {"list", "tuple"}:
        result = [unpack(v, tensors) for v in item]
        return tuple(result) if kind == "tuple" else result
    if kind == "literal":
        return item
    raise ValueError(f"Unknown archive node: {kind}")


def write_archive(path, value, workflow_sha256=""):
    tensors = {}
    tree = pack(value, tensors)
    save_file(tensors, str(path), metadata={"repair_conditioning_version": "1",
        "tree": json.dumps(tree), "workflow_sha256": workflow_sha256})


def read_archive(path):
    with safe_open(str(path), framework="pt", device="cpu") as reader:
        metadata = reader.metadata()
    if metadata.get("repair_conditioning_version") != "1":
        raise ValueError("Unrecognized conditioning archive")
    # Detach from the read-only file mapping, including on Windows where live
    # mappings prevent archive replacement or cleanup.
    tensors = {key: value.clone() for key, value in load_file(str(path), device="cpu").items()}
    return unpack(json.loads(metadata["tree"]), tensors)


class SaveRepairConditioning:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"positive": ("CONDITIONING",), "negative": ("CONDITIONING",),
            "latent": ("LATENT",), "prefix": ("STRING", {"default": "repair"}),
            "workflow_sha256": ("STRING", {"default": ""})}}

    RETURN_TYPES = ("STRING",)
    FUNCTION = "save"
    OUTPUT_NODE = True
    CATEGORY = "Barely Comfy/repair"

    def save(self, positive, negative, latent, prefix, workflow_sha256):
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", prefix):
            raise ValueError("Use a simple conditioning prefix")
        root = Path(folder_paths.get_input_directory()) / "repair_conditioning"
        root.mkdir(exist_ok=True)
        name = prefix + "-" + uuid.uuid4().hex[:12] + ".safetensors"
        path = root / name
        write_archive(path, {"positive": positive, "negative": negative, "latent": latent}, workflow_sha256)
        relative = "repair_conditioning/" + name
        return {"ui": {"text": [relative], "archive_sha256": [hashlib.sha256(path.read_bytes()).hexdigest()]},
                "result": (relative,)}


class LoadRepairConditioning:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"file": ("STRING", {"default": "repair_conditioning/"}),
                             "expected_sha256": ("STRING", {"default": ""})}}

    RETURN_TYPES = ("CONDITIONING", "CONDITIONING", "LATENT")
    FUNCTION = "load"
    CATEGORY = "Barely Comfy/repair"

    def load(self, file, expected_sha256=""):
        root = (Path(folder_paths.get_input_directory()) / "repair_conditioning").resolve()
        path = (Path(folder_paths.get_input_directory()) / file).resolve()
        if not path.is_relative_to(root) or path.suffix != ".safetensors":
            raise ValueError("Conditioning must be inside input/repair_conditioning")
        if expected_sha256 and hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha256:
            raise ValueError("Conditioning archive checksum changed")
        data = read_archive(path)
        return data["positive"], data["negative"], data["latent"]


NODE_CLASS_MAPPINGS = {"SaveRepairConditioning": SaveRepairConditioning, "LoadRepairConditioning": LoadRepairConditioning}
