#!/usr/bin/env python3
"""Convert the pinned jayn7 public GGUF example to a flat ComfyUI API graph.

This does not read the WeChat private-drive workflow, load models, or start a GPU.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
REVISION = "6e2dff8e3abd78051c1211fb5833a03818a2f3cc"
SOURCE = ROOT / "source_workflows" / "jayn7-example_workflow.json"
SOURCE_SHA256 = "db310e133dc39dee775a035a20d3d9246fb6c1f9a8f3da383919f4d783724a21"
MODEL_SHA256 = "745ec270db042409fde084d6b5cfccabf214a7fe5a494edf994a391125656afd"
ENCODER_SHA256 = "f6f851777709861056efcdad3af01da38b31223a3ba26e61a4f8bf3a2195813a"
VAE_SHA256 = "afc8e28272cd15db3919bacdb6918ce9c1ed22e96cb12c4d5ed0fba823529e38"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make() -> tuple[dict[str, Any], dict[str, Any]]:
    if digest(SOURCE) != SOURCE_SHA256:
        raise ValueError("Pinned jayn7 workflow digest changed")
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    nodes = {int(node["id"]): node for node in source["nodes"]}
    expected_types = {
        9: "UnetLoaderGGUF", 7: "CLIPLoaderGGUF", 11: "ModelSamplingAuraFlow",
        8: "CLIPTextEncode", 3: "CLIPTextEncode", 5: "EmptySD3LatentImage",
        10: "KSampler", 4: "VAELoader", 6: "VAEDecode", 18: "SaveImage",
    }
    for node_id, node_type in expected_types.items():
        node = nodes.get(node_id)
        if node is None or node["type"] != node_type or int(node.get("mode", 0)) != 0:
            raise ValueError(f"Source node {node_id} is not active {node_type}")
    # Exact active edge layout of the upstream public example. Link IDs are UI details.
    edges = {(int(link[1]), int(link[2]), int(link[3]), int(link[4])) for link in source["links"]}
    required = {
        (9, 0, 11, 0), (11, 0, 10, 0), (7, 0, 8, 0), (7, 0, 3, 0),
        (8, 0, 10, 1), (3, 0, 10, 2), (5, 0, 10, 3),
        (10, 0, 6, 0), (4, 0, 6, 1), (6, 0, 18, 0),
    }
    if edges != required:
        raise ValueError(f"Public example active graph changed: {edges ^ required}")
    source_sampler = nodes[10]["widgets_values"]
    seed, seed_mode, steps, cfg, sampler_name, scheduler, denoise = source_sampler
    if (steps, cfg, sampler_name, scheduler, denoise, nodes[11]["widgets_values"][0]) != (
        9, 1, "euler", "simple", 1, 3
    ):
        raise ValueError("Pinned public example sampling settings changed")
    if nodes[5]["widgets_values"] != [2048, 2048, 1]:
        raise ValueError("Pinned public example latent size changed")

    manifest = json.loads((ROOT / "download-manifest.json").read_text(encoding="utf-8"))
    required_files = {
        "z_image_turbo-Q4_K_M.gguf": ("jayn7/Z-Image-Turbo-GGUF", REVISION, MODEL_SHA256),
        "Qwen3-4B-Q4_K_M.gguf": ("unsloth/Qwen3-4B-GGUF", "22c9fc8a8c7700b76a1789366280a6a5a1ad1120", ENCODER_SHA256),
        "split_files/vae/ae.safetensors": ("Comfy-Org/z_image_turbo", "6fc90a3b1b653e935a0d175e260736de25b84df5", VAE_SHA256),
    }
    by_file = {item["file"]: item for item in manifest}
    for file, (repo, revision, sha256) in required_files.items():
        item = by_file[file]
        if (item["repo"], item["revision"], item["sha256"]) != (repo, revision, sha256):
            raise ValueError(f"Download manifest does not match pinned {file}")

    api = {
        "9": {"class_type": "UnetLoaderGGUF", "inputs": {"unet_name": "z_image_turbo-Q4_K_M.gguf"}},
        "7": {"class_type": "CLIPLoaderGGUF", "inputs": {"clip_name": "Qwen3-4B-Q4_K_M.gguf", "type": "lumina2"}},
        "11": {"class_type": "ModelSamplingAuraFlow", "inputs": {"model": ["9", 0], "shift": 3}},
        "8": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["7", 0], "text": nodes[8]["widgets_values"][0]}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["7", 0], "text": nodes[3]["widgets_values"][0]}},
        # 1024 square comes from the article screenshot; upstream example is 2048 square.
        "5": {"class_type": "EmptySD3LatentImage", "inputs": {"width": 1024, "height": 1024, "batch_size": 1}},
        "10": {"class_type": "KSampler", "inputs": {
            "model": ["11", 0], "positive": ["8", 0], "negative": ["3", 0],
            "latent_image": ["5", 0], "seed": seed, "steps": steps, "cfg": cfg,
            "sampler_name": sampler_name, "scheduler": scheduler, "denoise": denoise,
        }},
        "4": {"class_type": "VAELoader", "inputs": {"vae_name": "ae.safetensors"}},
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["10", 0], "vae": ["4", 0]}},
        "18": {"class_type": "SaveImage", "inputs": {"images": ["6", 0], "filename_prefix": "zimage/gguf-q4km"}},
    }
    bindings = {
        "source": {
            "repository": "jayn7/Z-Image-Turbo-GGUF", "revision": REVISION,
            "url": f"https://huggingface.co/jayn7/Z-Image-Turbo-GGUF/blob/{REVISION}/example_workflow.json",
            "snapshot": "source_workflows/jayn7-example_workflow.json",
            "snapshot_sha256": SOURCE_SHA256,
            "description": "Pinned public repository example converted to a flat API graph; not the article author's private-drive workflow",
        },
        "models": {
            "diffusion_model": by_file["z_image_turbo-Q4_K_M.gguf"],
            "text_encoder": by_file["Qwen3-4B-Q4_K_M.gguf"],
            "vae": by_file["split_files/vae/ae.safetensors"],
            "note": "Q4_K_M encoder was selected for this run; the offline article screenshot shows Q4_K_S, while its prose permits choosing a suitable quantization.",
        },
        "api_bindings": {
            "unet_loader_node_id": "9", "clip_loader_node_id": "7", "model_sampling_node_id": "11",
            "positive_prompt_node_id": "8", "negative_prompt_node_id": "3",
            "latent_size_node_id": "5", "sampler_node_id": "10", "vae_loader_node_id": "4",
            "vae_decode_node_id": "6", "save_image_node_id": "18",
            "sampler_seed_input": "seed", "sampler_steps_input": "steps",
            "save_image_filename_prefix_input": "filename_prefix",
        },
        "source_defaults": {
            "seed": seed, "seed_behavior": seed_mode,
            "steps": steps, "cfg": cfg, "sampler_name": sampler_name,
            "scheduler": scheduler, "denoise": denoise, "model_sampling_shift": 3,
            "positive_prompt": nodes[8]["widgets_values"][0],
            "negative_prompt": nodes[3]["widgets_values"][0],
            "source_width": 2048, "source_height": 2048,
            "trial_width": 1024, "trial_height": 1024,
            "resolution_reason": "Article image 006 flat GGUF graph shows 1024x1024; lower-resource first trial.",
        },
        "excluded_source_nodes": [
            {"id": int(node["id"]), "type": node["type"], "mode": int(node.get("mode", 0))}
            for node in source["nodes"] if int(node["id"]) not in expected_types
        ],
    }
    return api, bindings


def main() -> None:
    api, bindings = make()
    output = ROOT / "workflows"
    output.mkdir(exist_ok=True)
    (output / "gguf.api.json").write_text(json.dumps(api, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "bindings-gguf.json").write_text(json.dumps(bindings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Wrote pinned public GGUF example conversion and bindings")


if __name__ == "__main__":
    main()
