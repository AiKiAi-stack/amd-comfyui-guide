"""Narrow checks for configurations with retained local failure evidence."""
from pathlib import PurePosixPath


def known_workflow_errors(graph):
    errors = []
    def check_links(value, owner):
        if isinstance(value, list) and len(value) == 2 and isinstance(value[0], str) and isinstance(value[1], int):
            if value[0] not in graph:
                errors.append(f"Missing workflow node {value[0]} referenced by {owner}")
        elif isinstance(value, dict):
            for child in value.values():
                check_links(child, owner)
        elif isinstance(value, list):
            for child in value:
                check_links(child, owner)

    for node_id, node in graph.items():
        check_links(node.get("inputs", {}), node_id)
    for sampler_id, sampler in graph.items():
        if sampler.get("class_type") not in {"KSampler", "KSamplerAdvanced"}:
            continue
        current = sampler
        seen = set()
        sampling = None
        while True:
            link = current.get("inputs", {}).get("model")
            if not isinstance(link, list) or len(link) != 2 or not isinstance(link[0], str):
                break
            node_id = link[0]
            if node_id in seen or node_id not in graph:
                break
            seen.add(node_id)
            current = graph[node_id]
            kind = current.get("class_type", "")
            # The sampling override nearest to the sampler takes precedence.
            if sampling is None and kind.startswith("ModelSampling"):
                sampling = kind
            if kind == "UNETLoader":
                name = PurePosixPath(current.get("inputs", {}).get("unet_name", "").replace("\\", "/")).name
                if name == "moss_image_sft_int8_convrot.safetensors" and sampling == "ModelSamplingSD3":
                    errors.append(
                        f"MOSS timestep mismatch at sampler {sampler_id}: ModelSamplingSD3 sets the "
                        "wrong timestep scale for the tested moss_image_sft_int8_convrot model. "
                        "Use ModelSamplingAuraFlow with shift 5 (multiplier 1). "
                        "See trials/2026-10-18/moss-wrong-timestep-api.json and moss-api.json.")
                break
    return errors
