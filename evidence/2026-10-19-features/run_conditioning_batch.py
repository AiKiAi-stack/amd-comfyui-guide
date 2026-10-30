"""Run selected Kroma or Qwen cases in one dependency-ordered ComfyUI prompt.

The per-case builders remain the source of truth for all model inputs. This
script only namespaces node IDs and routes each sampler's positive conditioning
through BenchmarkConditioningBarrier nodes, which make every case's original
positive conditioning a dependency of every sampler.
"""

from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import shutil
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
COMFY = ROOT / "ComfyUI"
COMFY_OUTPUT = COMFY / "output"
COMFY_INPUT = COMFY / "input"
FEATURE_BENCH = HERE / "feature_bench.py"
BASE = "http://127.0.0.1:8188"
POLL_SECONDS = 5
TIMEOUT_SECONDS = 2400
MAX_CASES = 12
SAMPLER_TYPES = {"KSampler", "KSamplerAdvanced"}


def read_json(path: Path, fallback):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def load_feature_bench():
    spec = importlib.util.spec_from_file_location("feature_bench_for_conditioning_batch", FEATURE_BENCH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load graph builders from {FEATURE_BENCH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def is_link(value, node_ids: dict[str, str]) -> bool:
    return (
        isinstance(value, list)
        and len(value) == 2
        and str(value[0]) in node_ids
        and isinstance(value[1], int)
    )


def remap_links(value, node_ids: dict[str, str]):
    if is_link(value, node_ids):
        return [node_ids[str(value[0])], value[1]]
    if isinstance(value, dict):
        return {key: remap_links(item, node_ids) for key, item in value.items()}
    if isinstance(value, list):
        return [remap_links(item, node_ids) for item in value]
    return value


def find_sampler(graph: dict, case_id: str) -> tuple[str, dict]:
    samplers = [
        (str(node_id), node)
        for node_id, node in graph.items()
        if node.get("class_type") in SAMPLER_TYPES
        and "positive" in node.get("inputs", {})
    ]
    if len(samplers) != 1:
        raise ValueError(f"{case_id}: expected one KSampler, found {len(samplers)}")
    sampler_id, sampler = samplers[0]
    if not is_link(sampler["inputs"]["positive"], {str(key): str(key) for key in graph}):
        raise ValueError(f"{case_id}: sampler positive is not a node link")
    return sampler_id, sampler


def output_role(filename_prefix: str, case_id: str) -> str:
    normalized = str(filename_prefix).replace("\\", "/").rstrip("/")
    base = f"FeatureBench/{case_id}"
    if normalized == base:
        return "main"
    if normalized == base + "-mask":
        return "mask"
    if normalized == base + "-input":
        return "input"
    return "extra"


def build_batch_graph(cases: list[dict], model: str, feature_bench_module=None):
    """Build a namespaced batch graph without contacting ComfyUI."""
    if not 1 <= len(cases) <= MAX_CASES:
        raise ValueError(f"A batch must contain between 1 and {MAX_CASES} cases")
    if model not in ("kroma", "qwen"):
        raise ValueError(f"Unsupported model: {model}")
    if feature_bench_module is None:
        feature_bench_module = load_feature_bench()
    builder = {
        "kroma": feature_bench_module.kroma_graph,
        "qwen": feature_bench_module.qwen_graph,
    }[model]

    merged: dict[str, dict] = {}
    prepared: list[dict] = []
    all_positive_refs: list[list] = []
    shared_loader_ids = {}

    for index, case in enumerate(cases):
        case_id = str(case["id"])
        single_graph = builder(case)
        sampler_id, sampler = find_sampler(single_graph, case_id)
        original_positive = copy.deepcopy(sampler["inputs"]["positive"])
        prefix = f"case{index + 1:02d}_"
        node_ids = {str(node_id): prefix + str(node_id) for node_id in single_graph}
        # Explicitly reuse the same loaded objects, independent of cross-node
        # output-cache behavior. Only these reference-free file loaders merge.
        for node_id, candidate in single_graph.items():
            if candidate.get("class_type") in {"UnetLoaderGGUF", "CLIPLoader", "VAELoader"}:
                signature = json.dumps(candidate, sort_keys=True)
                shared_id = shared_loader_ids.setdefault(signature, node_ids[str(node_id)])
                node_ids[str(node_id)] = shared_id
        mapped_graph = {
            node_ids[str(node_id)]: remap_links(node, node_ids)
            for node_id, node in single_graph.items()
        }
        merged.update(mapped_graph)
        positive_ref = remap_links(original_positive, node_ids)
        all_positive_refs.append(positive_ref)

        output_nodes = []
        for original_node_id, node in single_graph.items():
            if node.get("class_type") != "SaveImage":
                continue
            filename_prefix = node.get("inputs", {}).get("filename_prefix", "")
            output_nodes.append({
                "original_node_id": str(original_node_id),
                "node_id": node_ids[str(original_node_id)],
                "filename_prefix": filename_prefix,
                "role": output_role(filename_prefix, case_id),
            })

        prepared.append({
            "case": case,
            "case_index": index,
            "single_graph": single_graph,
            "node_ids": node_ids,
            "sampler_id": node_ids[sampler_id],
            "positive_ref": positive_ref,
            "barrier_id": f"batch_barrier_{index + 1:02d}",
            "output_nodes": output_nodes,
            "merged_node_ids": list(mapped_graph),
        })

    for item in prepared:
        inputs = {"conditioning": item["positive_ref"]}
        for ready_index, positive_ref in enumerate(all_positive_refs, start=1):
            inputs[f"ready_{ready_index}"] = copy.deepcopy(positive_ref)
        merged[item["barrier_id"]] = {
            "class_type": "BenchmarkConditioningBarrier",
            "inputs": inputs,
        }
        merged[item["sampler_id"]]["inputs"]["positive"] = [item["barrier_id"], 0]

    return merged, prepared


def output_path(image: dict) -> Path | None:
    filename = image.get("filename")
    if not filename:
        return None
    candidate = COMFY_OUTPUT / str(image.get("subfolder", "")) / str(filename)
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(COMFY_OUTPUT.resolve())
        return resolved if resolved.is_file() else None
    except (OSError, ValueError):
        return None


def filename_matches_prefix(filename: str, filename_prefix: str) -> bool:
    base = str(filename_prefix).replace("\\", "/").rstrip("/").split("/")[-1]
    if not base or not filename.startswith(base):
        return False
    suffix = filename[len(base):]
    return not suffix or suffix[0] in "_."


def case_images(history: dict | None, item: dict) -> list[dict]:
    if not isinstance(history, dict):
        return []
    outputs = history.get("outputs", {})
    images = []
    for output_node in item["output_nodes"]:
        node_output = outputs.get(output_node["node_id"], {})
        if not isinstance(node_output, dict):
            continue
        for image in node_output.get("images", []):
            if not isinstance(image, dict):
                continue
            filename = str(image.get("filename", ""))
            if not filename_matches_prefix(filename, output_node["filename_prefix"]):
                continue
            path = output_path(image)
            if path is None:
                continue
            images.append({
                "path": str(path),
                "filename": filename,
                "subfolder": str(image.get("subfolder", "")),
                "filename_prefix": output_node["filename_prefix"],
                "node_id": output_node["node_id"],
                "role": output_node["role"],
            })
    return images


def execution_errors(history: dict | None) -> list[dict]:
    if not isinstance(history, dict):
        return []
    status = history.get("status", {})
    errors = []
    for message in status.get("messages", []):
        if not isinstance(message, (list, tuple)) or len(message) != 2:
            continue
        kind, detail = message
        if kind == "execution_error" and isinstance(detail, dict):
            errors.append({
                key: detail.get(key)
                for key in ("node_id", "node_type", "exception_type", "exception_message")
                if detail.get(key) is not None
            })
    return errors


def case_specific_errors(errors: list[dict], item: dict) -> list[dict]:
    node_ids = set(item["merged_node_ids"])
    node_ids.add(item["barrier_id"])
    return [error for error in errors if str(error.get("node_id", "")) in node_ids]


def batch_id_now() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}-{uuid.uuid4().hex[:8]}"


def save_batch_graph_artifacts(batch_graph: dict, prepared: list[dict], batch_id: str):
    batch_dir = HERE / "batches" / batch_id
    batch_dir.mkdir(parents=True, exist_ok=False)
    write_json(HERE / "batch-api.json", batch_graph)
    write_json(batch_dir / "batch-api.json", batch_graph)

    manifest = []
    for item in prepared:
        case = item["case"]
        case_dir = HERE / "cases" / str(case["id"])
        case_dir.mkdir(parents=True, exist_ok=True)
        write_json(case_dir / "single-api.json", item["single_graph"])
        write_json(case_dir / "api.json", batch_graph)
        manifest_item = {
            "id": case["id"],
            "model": case["model"],
            "sampler_node_id": item["sampler_id"],
            "barrier_node_id": item["barrier_id"],
            "output_nodes": item["output_nodes"],
        }
        manifest.append(manifest_item)
    write_json(batch_dir / "manifest.json", manifest)
    return batch_dir


def status_for_case(batch_status: str, images: list[dict], errors: list[dict]) -> str:
    main_output = any(image["role"] == "main" for image in images)
    normalized = batch_status.lower()
    if normalized in ("success", "completed", "complete"):
        return "success" if main_output else "success_no_output"
    if normalized in ("error", "failed", "failure"):
        if errors:
            return "error"
        return "partial_success" if images else "batch_error"
    return normalized or "unknown"


def write_case_result(item: dict, batch_id: str, prompt_id, batch_status: str,
                      batch_elapsed: float, submission, history, batch_error=None):
    case = item["case"]
    case_id = str(case["id"])
    case_dir = HERE / "cases" / case_id
    write_json(case_dir / "submission.json", submission)
    if isinstance(history, dict):
        write_json(case_dir / "history.json", history)

    images = case_images(history, item)
    errors = execution_errors(history)
    own_errors = case_specific_errors(errors, item)
    if batch_error is not None:
        case_status = "runner_error"
        own_errors = [{"exception_type": type(batch_error).__name__,
                       "exception_message": str(batch_error)}]
    else:
        case_status = status_for_case(batch_status, images, own_errors)

    record = {
        **case,
        "batch_id": batch_id,
        "prompt_id": prompt_id,
        "status": case_status,
        "batch_status": batch_status,
        "elapsed_seconds": None,
        "batch_elapsed_seconds": round(batch_elapsed, 2),
        "elapsed_scope": "whole batch; no per-case duration",
        "elapsed": f"批次总耗时 {batch_elapsed:.2f} 秒",
        "output_nodes": item["output_nodes"],
        "images": images,
        "errors": own_errors,
    }
    if batch_error is not None:
        record["error"] = str(batch_error)

    main_image = next((image for image in images if image["role"] == "main"), None)
    if case_status == "success" and main_image is not None:
        destination = COMFY_INPUT / "featurebench" / f"{case_id}.png"
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(main_image["path"], destination)
            record["copied_input"] = str(destination)
        except OSError as error:
            record["copy_error"] = str(error)

    write_json(case_dir / "result.json", record)
    return record


def selected_cases(model: str, case_ids: list[str], cases_path: Path):
    all_cases = read_json(cases_path, None)
    if not isinstance(all_cases, list):
        raise ValueError(f"Could not read case list: {cases_path}")
    by_id = {str(case.get("id")): case for case in all_cases if isinstance(case, dict)}
    missing = [case_id for case_id in case_ids if case_id not in by_id]
    if missing:
        raise ValueError("Unknown case id(s): " + ", ".join(missing))
    wrong_model = [case_id for case_id in case_ids if by_id[case_id].get("model") != model]
    if wrong_model:
        raise ValueError(f"Case(s) do not belong to model {model}: " + ", ".join(wrong_model))
    return [by_id[case_id] for case_id in case_ids]


def preflight(cases: list[dict]) -> tuple[list[dict], list[str]]:
    runnable = []
    skipped = []
    for case in cases:
        result_path = HERE / "cases" / str(case["id"]) / "result.json"
        if not result_path.exists():
            runnable.append(case)
            continue
        old = read_json(result_path, None)
        if isinstance(old, dict) and str(old.get("status", "")).lower() == "success":
            skipped.append(str(case["id"]))
            continue
        status = old.get("status", "unreadable") if isinstance(old, dict) else "unreadable"
        raise RuntimeError(
            f"Refusing to overwrite existing result for {case['id']} (status={status}). "
            "Preserve or explicitly review that evidence before retrying."
        )
    return runnable, skipped


def run_batch(model: str, case_ids: list[str]):
    if not case_ids or any(not case_id.strip() for case_id in case_ids):
        raise ValueError("--cases must contain one or more comma-separated case IDs")
    case_ids = [case_id.strip() for case_id in case_ids]
    if len(set(case_ids)) != len(case_ids):
        raise ValueError("Duplicate case IDs are not allowed")

    cases = selected_cases(model, case_ids, HERE / "cases.json")
    runnable, skipped = preflight(cases)
    if skipped:
        print("Skipped existing success: " + ", ".join(skipped), flush=True)
    if not runnable:
        print("Nothing to run.", flush=True)
        return 0
    if len(runnable) > MAX_CASES:
        raise ValueError(f"At most {MAX_CASES} new cases can run in one batch")

    feature_bench = load_feature_bench()
    batch_graph, prepared = build_batch_graph(runnable, model, feature_bench)
    batch_id = batch_id_now()
    batch_dir = save_batch_graph_artifacts(batch_graph, prepared, batch_id)
    started_at = datetime.now(timezone.utc).isoformat()
    started_clock = time.monotonic()
    prompt_id = None
    submission = None
    history = None
    stage = "submission"

    try:
        response = requests.post(BASE + "/prompt", json={"prompt": batch_graph}, timeout=60)
        try:
            submission = response.json()
        except ValueError:
            submission = {"raw_text": response.text, "http_status": response.status_code}
        write_json(batch_dir / "submission.json", submission)
        response.raise_for_status()
        if not isinstance(submission, dict) or submission.get("error"):
            raise RuntimeError(f"ComfyUI rejected batch: {submission}")
        prompt_id = submission.get("prompt_id")
        if not prompt_id:
            raise RuntimeError(f"ComfyUI returned no prompt_id: {submission}")

        stage = "history"
        print(f"SUBMITTED batch={batch_id} prompt_id={prompt_id} cases={len(prepared)}", flush=True)
        deadline = time.monotonic() + TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            try:
                response = requests.get(BASE + "/history/" + str(prompt_id), timeout=30)
            except requests.ReadTimeout:
                print("History API busy; keep waiting for the existing prompt, do not resubmit", flush=True)
                time.sleep(POLL_SECONDS)
                continue
            response.raise_for_status()
            history_response = response.json()
            history = history_response.get(str(prompt_id)) if isinstance(history_response, dict) else None
            if history:
                break
            time.sleep(POLL_SECONDS)
        if not history:
            raise TimeoutError(f"No history received for prompt_id={prompt_id} within {TIMEOUT_SECONDS} seconds")

        write_json(batch_dir / "history.json", history)
        batch_status = str(history.get("status", {}).get("status_str", "unknown"))
        batch_elapsed = time.monotonic() - started_clock
        records = [
            write_case_result(item, batch_id, prompt_id, batch_status, batch_elapsed,
                              submission, history)
            for item in prepared
        ]
        print(json.dumps({
            "batch_id": batch_id,
            "prompt_id": prompt_id,
            "batch_status": batch_status,
            "batch_elapsed_seconds": round(batch_elapsed, 2),
            "cases": [{"id": record["id"], "status": record["status"],
                       "images": len(record["images"])} for record in records],
        }, ensure_ascii=False), flush=True)
        if batch_status.lower() not in ("success", "completed", "complete"):
            return 1
        return 0
    except Exception as error:
        batch_elapsed = time.monotonic() - started_clock
        failure = {
            "batch_id": batch_id,
            "stage": stage,
            "started_at": started_at,
            "failed_at": datetime.now(timezone.utc).isoformat(),
            "prompt_id": prompt_id,
            "exception_type": type(error).__name__,
            "exception_message": str(error),
            "batch_elapsed_seconds": round(batch_elapsed, 2),
        }
        write_json(batch_dir / "failure.json", failure)
        if isinstance(history, dict):
            write_json(batch_dir / "history.json", history)
        failure_status = "timeout" if isinstance(error, TimeoutError) else "runner_error"
        for item in prepared:
            case_dir = HERE / "cases" / str(item["case"]["id"])
            write_json(case_dir / "submission.json", submission if submission is not None else failure)
            if isinstance(history, dict):
                write_json(case_dir / "history.json", history)
            record = {
                **item["case"],
                "batch_id": batch_id,
                "prompt_id": prompt_id,
                "status": failure_status,
                "batch_status": failure_status,
                "elapsed_seconds": None,
                "batch_elapsed_seconds": round(batch_elapsed, 2),
                "elapsed_scope": "whole batch; no per-case duration",
                "elapsed": f"批次总耗时 {batch_elapsed:.2f} 秒",
                "output_nodes": item["output_nodes"],
                "images": case_images(history, item),
                "errors": [{"exception_type": type(error).__name__,
                            "exception_message": str(error)}],
                "error": str(error),
            }
            write_json(case_dir / "result.json", record)
        print(f"BATCH FAILED ({stage}): {type(error).__name__}: {error}", flush=True)
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", choices=("kroma", "qwen"))
    parser.add_argument("--cases", required=True, help="Comma-separated case IDs from cases.json")
    args = parser.parse_args()
    try:
        return run_batch(args.model, args.cases.split(","))
    except Exception as error:
        parser.exit(2, f"error: {type(error).__name__}: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
