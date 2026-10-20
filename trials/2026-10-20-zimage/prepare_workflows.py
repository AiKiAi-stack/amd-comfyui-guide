#!/usr/bin/env python3
"""Convert the pinned legacy Z-Image-Turbo-AIO workflow to a small API prompt.

This is a local, offline conversion of the source workflow. It does not load a
model, contact ComfyUI, download weights, or create/modify trial case files.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


REVISION = "3614ae1a6ceec70d8b1b02f41df3af72ac756241"
WORKFLOW_SHA256 = "1ef90efdc7c84a93e7c036dcd2a346027514511b7fa88857f1df329722f68053"
FP8_SHA256 = "f569c42b6797a89e65e80c743d6dfd230ed9318237aa242c92777deb22fad660"
FP8_BYTES = 10_345_190_658


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_node(nodes: dict[int, dict[str, Any]], node_id: int, node_type: str) -> dict[str, Any]:
    node = nodes.get(node_id)
    if node is None or node.get("type") != node_type:
        raise ValueError(f"Expected source node {node_id} to be {node_type}")
    return node


def convert() -> tuple[dict[str, Any], dict[str, Any]]:
    root = Path(__file__).resolve().parent
    source_dir = root / "source_workflows"
    source_path = source_dir / "z-image-turbo-aio-workflow.json"
    metadata_path = source_dir / f"api-model-revision-{REVISION}.json"
    output_dir = root / "workflows"

    if not source_path.is_file() or not metadata_path.is_file():
        raise FileNotFoundError("Pinned source workflow or Hugging Face metadata is missing")
    if sha256(source_path) != WORKFLOW_SHA256:
        raise ValueError("Pinned workflow SHA-256 does not match the audited source")

    source = json.loads(source_path.read_text(encoding="utf-8"))
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if metadata.get("sha") != REVISION:
        raise ValueError("Hugging Face metadata is not for the pinned revision")

    siblings = {item["rfilename"]: item for item in metadata["siblings"]}
    checkpoint = siblings["z-image-turbo-fp8-aio.safetensors"]
    workflow_meta = siblings["z-image-turbo-aio-workflow.json"]
    if checkpoint.get("size") != FP8_BYTES or checkpoint.get("lfs", {}).get("sha256") != FP8_SHA256:
        raise ValueError("FP8 checkpoint metadata no longer matches the audited identity")
    if workflow_meta.get("size") != source_path.stat().st_size:
        raise ValueError("Saved workflow size does not match its pinned API metadata")

    nodes = {int(node["id"]): node for node in source["nodes"]}
    links = source["links"]
    # The source's links are [link_id, from_node, from_slot, to_node, to_slot, type].
    incoming: dict[tuple[int, int], tuple[int, int]] = {}
    for link in links:
        _, from_node, from_slot, to_node, to_slot, _ = link
        key = (int(to_node), int(to_slot))
        if key in incoming:
            raise ValueError(f"Multiple source links feed input {key}")
        incoming[key] = (int(from_node), int(from_slot))

    def resolve_output(node_id: int, output_slot: int, seen: set[tuple[int, int]] | None = None) -> tuple[str, int]:
        """Resolve only source-verified reroutes and the disabled LoRA bypass."""
        seen = set() if seen is None else seen
        marker = (node_id, output_slot)
        if marker in seen:
            raise ValueError(f"Cycle detected while resolving source output {marker}")
        seen.add(marker)
        node = nodes[node_id]
        node_type = node["type"]

        if node_type == "Reroute":
            upstream = incoming.get((node_id, 0))
            if upstream is None:
                raise ValueError(f"Unconnected source Reroute node {node_id}")
            return resolve_output(*upstream, seen)

        if node_type == "LoraLoader" and int(node.get("mode", 0)) == 4:
            # ComfyUI mode=4 is bypass. Model and CLIP output slots pass through
            # their matching loader inputs; the LoRA is intentionally excluded.
            upstream = incoming.get((node_id, output_slot))
            if upstream is None:
                raise ValueError(f"Bypassed LoRA output {node_id}:{output_slot} has no input")
            return resolve_output(*upstream, seen)

        return str(node_id), output_slot

    def source_for_input(node_id: int, input_name: str) -> tuple[str, int]:
        node = nodes[node_id]
        input_slots = [i for i, item in enumerate(node.get("inputs", [])) if item.get("name") == input_name]
        if len(input_slots) != 1:
            raise ValueError(f"Expected one source input named {input_name!r} on node {node_id}")
        upstream = incoming.get((node_id, input_slots[0]))
        if upstream is None:
            raise ValueError(f"Source input {node_id}.{input_name} is not connected")
        return resolve_output(*upstream)

    checkpoint_node = require_node(nodes, 34, "CheckpointLoaderSimple")
    sampling_node = require_node(nodes, 2, "ModelSamplingAuraFlow")
    prompt_node = require_node(nodes, 20, "CLIPTextEncode")
    zero_node = require_node(nodes, 40, "ConditioningZeroOut")
    latent_node = require_node(nodes, 6, "EmptyLatentImage")
    sampler_node = require_node(nodes, 17, "KSampler")
    decode_node = require_node(nodes, 11, "VAEDecode")
    save_node = require_node(nodes, 26, "SaveImage")
    lora_node = require_node(nodes, 41, "LoraLoader")

    for node in (checkpoint_node, sampling_node, prompt_node, zero_node, latent_node, sampler_node, decode_node, save_node):
        if int(node.get("mode", 0)) != 0:
            raise ValueError(f"Required source node {node['id']} is not active")
    if int(lora_node.get("mode", 0)) != 4:
        raise ValueError("Source LoRA is no longer bypassed; inspect before generating an API prompt")

    checkpoint_name = checkpoint_node["widgets_values"][0]
    seed, seed_behavior, steps, cfg, sampler_name, scheduler, denoise = sampler_node["widgets_values"]
    width, height, batch_size = latent_node["widgets_values"]
    shift = sampling_node["widgets_values"][0]
    positive_clip = source_for_input(prompt_node["id"], "clip")
    lora_model = source_for_input(sampling_node["id"], "model")
    lora_clip = positive_clip
    zero_conditioning = source_for_input(zero_node["id"], "conditioning")
    negative_conditioning = source_for_input(sampler_node["id"], "negative")
    sampler_model = source_for_input(sampler_node["id"], "model")
    sampler_positive = source_for_input(sampler_node["id"], "positive")
    sampler_latent = source_for_input(sampler_node["id"], "latent_image")
    decode_samples = source_for_input(decode_node["id"], "samples")
    decode_vae = source_for_input(decode_node["id"], "vae")
    save_images = source_for_input(save_node["id"], "images")

    # Check the resolved graph against the original active graph after removing
    # only the bypassed LoRA and UI-only reroute layers.
    expected = {
        "model_sampling": (str(checkpoint_node["id"]), 0),
        "prompt_clip": (str(checkpoint_node["id"]), 1),
        "zero_conditioning": (str(prompt_node["id"]), 0),
        "sampler_model": (str(sampling_node["id"]), 0),
        "sampler_positive": (str(prompt_node["id"]), 0),
        "sampler_negative": (str(zero_node["id"]), 0),
        "sampler_latent": (str(latent_node["id"]), 0),
        "decode_samples": (str(sampler_node["id"]), 0),
        "decode_vae": (str(checkpoint_node["id"]), 2),
        "save_images": (str(decode_node["id"]), 0),
    }
    actual = {
        "model_sampling": lora_model,
        "prompt_clip": positive_clip,
        "zero_conditioning": zero_conditioning,
        "sampler_model": sampler_model,
        "sampler_positive": sampler_positive,
        "sampler_negative": negative_conditioning,
        "sampler_latent": sampler_latent,
        "decode_samples": decode_samples,
        "decode_vae": decode_vae,
        "save_images": save_images,
    }
    if actual != expected:
        raise ValueError(f"Resolved graph differs from audited source: {actual}")

    api = {
        str(checkpoint_node["id"]): {
            "inputs": {"ckpt_name": checkpoint_name},
            "class_type": "CheckpointLoaderSimple",
        },
        str(sampling_node["id"]): {
            "inputs": {"model": [*lora_model], "shift": shift},
            "class_type": "ModelSamplingAuraFlow",
        },
        str(prompt_node["id"]): {
            "inputs": {"clip": [*lora_clip], "text": prompt_node["widgets_values"][0]},
            "class_type": "CLIPTextEncode",
        },
        str(zero_node["id"]): {
            "inputs": {"conditioning": [*zero_conditioning]},
            "class_type": "ConditioningZeroOut",
        },
        str(latent_node["id"]): {
            "inputs": {"width": width, "height": height, "batch_size": batch_size},
            "class_type": "EmptyLatentImage",
        },
        str(sampler_node["id"]): {
            "inputs": {
                "model": [*sampler_model],
                "positive": [*sampler_positive],
                "negative": [*negative_conditioning],
                "latent_image": [*sampler_latent],
                "seed": seed,
                "steps": steps,
                "cfg": cfg,
                "sampler_name": sampler_name,
                "scheduler": scheduler,
                "denoise": denoise,
            },
            "class_type": "KSampler",
        },
        str(decode_node["id"]): {
            "inputs": {"samples": [*decode_samples], "vae": [*decode_vae]},
            "class_type": "VAEDecode",
        },
        str(save_node["id"]): {
            "inputs": {
                "images": [*save_images],
                "filename_prefix": save_node["widgets_values"][0],
            },
            "class_type": "SaveImage",
        },
    }

    excluded_types = {
        "Image Comparer (rgthree)",
        "Fast Groups Bypasser (rgthree)",
        "MarkdownNote",
        "Reroute",
    }
    excluded_nodes = [
        {"id": int(node["id"]), "type": node["type"], "reason": "UI-only or resolved passthrough"}
        for node in source["nodes"]
        if node["type"] in excluded_types or (node["type"] == "LoraLoader" and int(node.get("mode", 0)) == 4)
    ]
    inactive_nodes = [
        {"id": int(node["id"]), "type": node["type"], "mode": int(node.get("mode", 0)), "widgets": node.get("widgets_values", [])}
        for node in source["nodes"]
        if int(node.get("mode", 0)) != 0 and node["type"] not in excluded_types
    ]

    bindings = {
        "source": {
            "repository": "SeeSee21/Z-Image-Turbo-AIO",
            "revision": REVISION,
            "source_workflow": "source_workflows/z-image-turbo-aio-workflow.json",
            "source_workflow_sha256": WORKFLOW_SHA256,
            "metadata": f"source_workflows/api-model-revision-{REVISION}.json",
        },
        "checkpoint": {
            "source_filename": checkpoint_name,
            "expected_bytes": FP8_BYTES,
            "expected_sha256": FP8_SHA256,
            "ComfyUI_model_directory": "models/checkpoints",
        },
        "api_bindings": {
            "checkpoint_node_id": str(checkpoint_node["id"]),
            "model_sampling_node_id": str(sampling_node["id"]),
            "positive_prompt_node_id": str(prompt_node["id"]),
            "negative_conditioning_node_id": str(zero_node["id"]),
            "latent_size_node_id": str(latent_node["id"]),
            "sampler_node_id": str(sampler_node["id"]),
            "sampler_seed_input": "seed",
            "sampler_steps_input": "steps",
            "sampler_cfg_input": "cfg",
            "sampler_name_input": "sampler_name",
            "sampler_scheduler_input": "scheduler",
            "sampler_denoise_input": "denoise",
            "vae_decode_node_id": str(decode_node["id"]),
            "save_image_node_id": str(save_node["id"]),
            "save_image_filename_prefix_input": "filename_prefix",
        },
        "source_defaults": {
            "positive_prompt": prompt_node["widgets_values"][0],
            "seed": seed,
            "seed_behavior": seed_behavior,
            "steps": steps,
            "cfg": cfg,
            "sampler_name": sampler_name,
            "scheduler": scheduler,
            "denoise": denoise,
            "model_sampling_shift": shift,
            "width": width,
            "height": height,
            "batch_size": batch_size,
            "filename_prefix": save_node["widgets_values"][0],
            "lora": {
                "source_node_id": str(lora_node["id"]),
                "source_mode": int(lora_node["mode"]),
                "source_filename": lora_node["widgets_values"][0],
                "included_in_api_prompt": False,
                "reason": "The exact pinned source workflow has this optional LoRA node in bypass mode.",
            },
        },
        "step_case_overrides": {
            "source_workflow_active": {"steps": steps, "meaning": "Exact active KSampler value in the pinned workflow."},
            "article_8_step": {"steps": 8, "meaning": "Article and pinned README recommendation; override only the KSampler steps field."},
            "article_4_step_comparison": {"steps": 4, "meaning": "Article's speed comparison; not the pinned workflow default or a separately verified optimum."},
            "all_variants_keep": {"cfg": cfg, "sampler_name": sampler_name, "scheduler": scheduler, "denoise": denoise, "model_sampling_shift": shift},
        },
        "excluded_or_inactive_nodes": {
            "excluded_from_api": excluded_nodes,
            "inactive_source_nodes": inactive_nodes,
            "notes": [
                "The active base branch is preserved. The optional high-resolution branch is bypassed in the source workflow.",
                "The rgthree toggle and comparison nodes are UI helpers and are omitted from the API prompt.",
            ],
        },
    }
    return api, bindings


def main() -> None:
    api, bindings = convert()
    output_dir = Path(__file__).resolve().parent / "workflows"
    output_dir.mkdir(exist_ok=True)
    (output_dir / "aio.api.json").write_text(json.dumps(api, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output_dir / "bindings-aio.json").write_text(json.dumps(bindings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {output_dir / 'aio.api.json'} and {output_dir / 'bindings-aio.json'}")


if __name__ == "__main__":
    main()
