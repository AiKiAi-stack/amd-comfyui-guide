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


def check_finite(tensor, path="tensor"):
    if (tensor.is_floating_point() or tensor.is_complex()) and not torch.isfinite(tensor).all().item():
        raise ValueError("Non-finite tensor; refusing invalid conditioning or sampled latent: "
                         f"path={path}, shape={tuple(tensor.shape)}, dtype={tensor.dtype}, "
                         f"nan={torch.isnan(tensor).sum().item()}, inf={torch.isinf(tensor).sum().item()}")


def pack(value, tensors, path="root"):
    if isinstance(value, torch.Tensor):
        if hasattr(value, "_qdata"):
            raise TypeError("Expected dense conditioning, received quantized model storage")
        key = f"tensor_{len(tensors)}"
        # Positive/negative conditions can share storage; safetensors requires
        # independent buffers for separate names.
        tensor = value.detach().to("cpu").contiguous().clone()
        check_finite(tensor, path)
        tensors[key] = tensor
        return ["tensor", key]
    if isinstance(value, dict):
        return ["dict", [[pack(k, tensors, path + ".key"), pack(v, tensors, path + "." + str(k))] for k, v in value.items()]]
    if isinstance(value, tuple):
        return ["tuple", [pack(v, tensors, f"{path}[{i}]") for i, v in enumerate(value)]]
    if isinstance(value, list):
        return ["list", [pack(v, tensors, f"{path}[{i}]") for i, v in enumerate(value)]]
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
    for tensor in tensors.values():
        check_finite(tensor)
    return unpack(json.loads(metadata["tree"]), tensors)


def save_payload(value, prefix, workflow_sha256):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", prefix):
        raise ValueError("Use a simple conditioning prefix")
    root = Path(folder_paths.get_input_directory()) / "repair_conditioning"
    root.mkdir(exist_ok=True)
    name = prefix + "-" + uuid.uuid4().hex[:12] + ".safetensors"
    path = root / name
    write_archive(path, value, workflow_sha256)
    relative = "repair_conditioning/" + name
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {"ui": {"text": [relative, "SHA256: " + digest], "archive_sha256": [digest]},
            "result": (relative,)}


def load_payload(file, expected_sha256):
    root = (Path(folder_paths.get_input_directory()) / "repair_conditioning").resolve()
    path = (Path(folder_paths.get_input_directory()) / file).resolve()
    if not path.is_relative_to(root) or path.suffix != ".safetensors":
        raise ValueError("Conditioning must be inside input/repair_conditioning")
    if expected_sha256 and hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha256:
        raise ValueError("Conditioning archive checksum changed")
    return read_archive(path)


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
        return save_payload({"positive": positive, "negative": negative, "latent": latent}, prefix, workflow_sha256)


class LoadRepairConditioning:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"file": ("STRING", {"default": "repair_conditioning/"}),
                             "expected_sha256": ("STRING", {"default": ""})}}

    RETURN_TYPES = ("CONDITIONING", "CONDITIONING", "LATENT")
    FUNCTION = "load"
    CATEGORY = "Barely Comfy/repair"

    def load(self, file, expected_sha256=""):
        data = load_payload(file, expected_sha256)
        return data["positive"], data["negative"], data["latent"]


class SaveRepairText:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"text": ("STRING", {"multiline": True}),
            "prefix": ("STRING", {"default": "caption"}),
            "workflow_sha256": ("STRING", {"default": ""})}}

    RETURN_TYPES = ("STRING",)
    FUNCTION = "save"
    OUTPUT_NODE = True
    CATEGORY = "Barely Comfy/repair"

    def save(self, text, prefix, workflow_sha256):
        result = save_payload({"kind": "repair_text_v1", "text": text}, prefix, workflow_sha256)
        result["ui"]["caption"] = [text]
        result["ui"]["text"].append(text)
        return result


class LoadRepairText:
    INPUT_TYPES = LoadRepairConditioning.INPUT_TYPES
    RETURN_TYPES = ("STRING",)
    FUNCTION = "load"
    CATEGORY = "Barely Comfy/repair"

    def load(self, file, expected_sha256=""):
        if not expected_sha256:
            raise ValueError("A verified text archive SHA is required")
        data = load_payload(file, expected_sha256)
        if data.get("kind") != "repair_text_v1" or not isinstance(data.get("text"), str):
            raise ValueError("Not a text archive")
        return (data["text"],)


class SaveRepairLatent:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"latent": ("LATENT",), "prefix": ("STRING", {"default": "sampled"}),
                             "workflow_sha256": ("STRING", {"default": ""})}}

    RETURN_TYPES = ("STRING",)
    FUNCTION = "save"
    OUTPUT_NODE = True
    CATEGORY = "Barely Comfy/repair"

    def save(self, latent, prefix, workflow_sha256):
        return save_payload({"latent": latent}, prefix, workflow_sha256)


class LoadRepairLatent:
    INPUT_TYPES = LoadRepairConditioning.INPUT_TYPES
    RETURN_TYPES = ("LATENT",)
    FUNCTION = "load"
    CATEGORY = "Barely Comfy/repair"

    def load(self, file, expected_sha256=""):
        return (load_payload(file, expected_sha256)["latent"],)


def qwen_reference_payload(vae, images, resolution, initial_latent=None):
    """Use the installed node's exact resize/alpha/latent preparation, without a TE."""
    from comfy_extras.nodes_qwen import TextEncodeQwenImage21

    resized, latents = [], []

    class CaptureVae:
        def encode(self, pixels):
            resized.append(pixels.detach().cpu().clone())
            latent = vae.encode(pixels)
            latents.append(latent)
            return latent

    class NoTextModel:
        def tokenize(self, *args, **kwargs):
            return None

        def encode_from_tokens_scheduled(self, tokens):
            return []

    output = TextEncodeQwenImage21.execute(NoTextModel(), '', '', vae=CaptureVae(),
                                         resolution=resolution, images=images)
    if not resized:
        raise ValueError('At least one Qwen image reference is required')
    return {'kind': 'repair_qwen21_references_v1', 'resized_images': resized,
            'reference_latents': latents,
            'initial_latent': initial_latent if initial_latent is not None else output.result[2]}


def encode_qwen_reference_payload(clip, prompt, negative_prompt, payload):
    """Call the real text node with cached VAE results and no resident VAE model."""
    from comfy_extras.nodes_qwen import TextEncodeQwenImage21
    if payload.get('kind') != 'repair_qwen21_references_v1':
        raise ValueError('Not a Qwen 2.1 reference archive')
    images, latents = payload['resized_images'], payload['reference_latents']
    if not images or len(images) != len(latents):
        raise ValueError('Reference image/latent count mismatch')

    class CachedVae:
        index = 0

        def encode(self, pixels):
            index = self.index
            if index >= len(images) or not torch.equal(pixels, images[index]):
                raise ValueError('Core reference preprocessing changed; recompute references')
            self.index += 1
            return latents[index]

    cache = CachedVae()
    output = TextEncodeQwenImage21.execute(clip, prompt, negative_prompt, vae=cache, resolution=0,
        images={f'image_{i + 1}': image for i, image in enumerate(images)})
    if cache.index != len(images):
        raise ValueError('Core did not consume every cached reference')
    return output.result[0], output.result[1], payload['initial_latent']


class SaveRepairQwenReferences:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'vae': ('VAE',), 'image1': ('IMAGE',),
            'resolution': ('INT', {'default': 512, 'min': 0, 'max': 4096, 'step': 32}),
            'prefix': ('STRING', {'default': 'qwen-references'}),
            'workflow_sha256': ('STRING', {'default': ''})},
            'optional': {'image2': ('IMAGE',), 'initial_latent': ('LATENT',)}}

    RETURN_TYPES = ('STRING',)
    FUNCTION = 'save'
    OUTPUT_NODE = True
    CATEGORY = 'Barely Comfy/repair'

    def save(self, vae, image1, resolution, prefix, workflow_sha256, image2=None, initial_latent=None):
        images = {'image_1': image1}
        if image2 is not None:
            images['image_2'] = image2
        payload = qwen_reference_payload(vae, images, resolution, initial_latent)
        return save_payload(payload, prefix, workflow_sha256)


class TextEncodeRepairQwenReferences:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'clip': ('CLIP',), 'prompt': ('STRING', {'multiline': True}),
            'negative_prompt': ('STRING', {'multiline': True}),
            'file': ('STRING', {'default': 'repair_conditioning/'}),
            'expected_sha256': ('STRING', {'default': ''})}}

    RETURN_TYPES = ('CONDITIONING', 'CONDITIONING', 'LATENT')
    FUNCTION = 'encode'
    CATEGORY = 'Barely Comfy/repair'

    def encode(self, clip, prompt, negative_prompt, file, expected_sha256):
        if not expected_sha256:
            raise ValueError('A verified reference archive SHA is required')
        return encode_qwen_reference_payload(clip, prompt, negative_prompt,
                                              load_payload(file, expected_sha256))


NODE_CLASS_MAPPINGS = {"SaveRepairConditioning": SaveRepairConditioning, "LoadRepairConditioning": LoadRepairConditioning,
                       "SaveRepairText": SaveRepairText, "LoadRepairText": LoadRepairText,
                       "SaveRepairLatent": SaveRepairLatent, "LoadRepairLatent": LoadRepairLatent,
                       'SaveRepairQwenReferences': SaveRepairQwenReferences,
                       'TextEncodeRepairQwenReferences': TextEncodeRepairQwenReferences}
