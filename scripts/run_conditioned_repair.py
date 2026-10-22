"""Isolate encoding, sampling and optional CPU decode, retaining exact tensors and bindings."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import shutil
import sys

from workflow_checks import known_workflow_errors


def prune(graph, roots):
    needed = set()

    def visit(key):
        if key in needed:
            return
        needed.add(key)

        def links(value):
            if isinstance(value, list) and len(value) == 2 and isinstance(value[0], str) and value[0] in graph and isinstance(value[1], int):
                visit(value[0])
            elif isinstance(value, dict):
                for child in value.values():
                    links(child)
            elif isinstance(value, list):
                for child in value:
                    links(child)
        links(graph[key]["inputs"])

    for root in roots:
        visit(root)
    return {k: v for k, v in graph.items() if k in needed}


def conditioning_signature(graph):
    """Ignore provenance-only digest when checking archived condition reuse."""
    graph = copy.deepcopy(graph)
    graph["repair_save_conditions"]["inputs"].pop("workflow_sha256", None)
    return hashlib.sha256(json.dumps(graph, sort_keys=True).encode()).hexdigest()


def sampling_signature(graph):
    graph = copy.deepcopy(graph)
    graph.get("repair_save_latent", {}).get("inputs", {}).pop("workflow_sha256", None)
    return hashlib.sha256(json.dumps(graph, sort_keys=True).encode()).hexdigest()


def conditioning_node(graph, sampler_id):
    sampler = graph[sampler_id]
    if sampler["class_type"] == "KSampler":
        return sampler_id
    link = sampler["inputs"].get("guider")
    if not isinstance(link, list) or len(link) != 2 or link[1] != 0 or graph[link[0]]["class_type"] != "CFGGuider":
        raise ValueError("SamplerCustomAdvanced requires a direct CFGGuider for condition isolation")
    return link[0]


def latent_sampling_graph(graph, sampler_id, label, digest):
    graph = copy.deepcopy(graph)
    graph["repair_save_latent"] = {"class_type": "SaveRepairLatent", "inputs": {
        "latent": [sampler_id, 0], "prefix": label, "workflow_sha256": digest}}
    return prune(graph, ["repair_save_latent"])


def latent_decode_graph(graph, sampler_id, output_ids, relative, digest):
    graph = copy.deepcopy(graph)
    graph[sampler_id] = {"class_type": "LoadRepairLatent", "inputs": {
        "file": relative, "expected_sha256": digest}}
    return prune(graph, output_ids)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--workflow", type=Path, nargs="+", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=1200)
    parser.add_argument("--gpu-chunked-logits", action="store_true",
                        help="Bound the INT8 vocabulary projection when the encoding graph generates text")
    parser.add_argument("--sample-extra-arg", action="append", default=[])
    parser.add_argument("--encode-extra-arg", action="append", default=[])
    parser.add_argument("--model-paths", type=Path)
    parser.add_argument("--python-executable", type=Path)
    parser.add_argument("--encoding-profile", choices=["gpu-text", "gpu-text-dynamic", "cpu-text"], default="gpu-text")
    parser.add_argument("--sampling-profile", choices=["gpu-text", "gpu-text-dynamic", "kroma"], default="gpu-text")
    parser.add_argument("--resume-encoding", type=Path,
                        help="Reuse successful conditions only when the complete encoding graph matches")
    parser.add_argument("--resume-sampling", type=Path,
                        help="With --isolate-decode, reuse successful identical sampling graphs; retry failed cases")
    parser.add_argument("--qwen-cache-device", choices=["auto", "gpu", "cpu", "off"])
    parser.add_argument("--isolate-sampling", action="store_true",
                        help="Use a fresh owned process per sample workflow to bound cross-case memory retention")
    parser.add_argument("--isolate-decode", action="store_true",
                        help="Save sampled latents, exit the GPU process, then decode/composite on CPU")
    args = parser.parse_args()
    if args.resume_sampling and not args.isolate_decode:
        parser.error("--resume-sampling requires --isolate-decode")
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    specs = []
    for workflow in args.workflow:
        label = workflow.stem.removesuffix(".api")
        if any(spec["label"] == label for spec in specs):
            parser.error("Workflow basenames must be unique")
        graph = json.loads(workflow.read_text(encoding="utf-8"))
        errors = known_workflow_errors(graph)
        if errors:
            parser.error("; ".join(errors))
        if args.qwen_cache_device:
            for node in graph.values():
                if node["class_type"] == "QwenImage21Cache":
                    node["inputs"]["device"] = args.qwen_cache_device
        sampler_ids = [k for k, n in graph.items() if n["class_type"] in {"KSampler", "SamplerCustomAdvanced"}]
        output_ids = [k for k, n in graph.items() if n["class_type"] == "SaveImage"]
        if len(sampler_ids) != 1 or not output_ids:
            parser.error("Use independent workflows with one KSampler or SamplerCustomAdvanced/CFGGuider and SaveImage")
        sampler_id = sampler_ids[0]
        conditioning_id = conditioning_node(graph, sampler_id)
        effective_bytes = json.dumps(graph, indent=2, ensure_ascii=False).encode("utf-8") if args.qwen_cache_device else workflow.read_bytes()
        digest = hashlib.sha256(effective_bytes).hexdigest()
        encode = copy.deepcopy(graph)
        inputs = graph[sampler_id]["inputs"]
        conditions = graph[conditioning_id]["inputs"]
        encode["repair_save_conditions"] = {"class_type": "SaveRepairConditioning", "inputs": {
            "positive": conditions["positive"], "negative": conditions["negative"], "latent": inputs["latent_image"],
            "prefix": label, "workflow_sha256": digest}}
        case_dir = out / "graphs" / label
        case_dir.mkdir(parents=True)
        encode_path = case_dir / (label + ".api.json")
        encode_path.write_text(json.dumps(prune(encode, ["repair_save_conditions"]), indent=2, ensure_ascii=False), encoding="utf-8")
        (case_dir / "original.json").write_bytes(workflow.read_bytes())
        (case_dir / "effective-workflow.api.json").write_bytes(effective_bytes)
        specs.append({"label": label, "graph": graph, "sampler": sampler_id, "conditioning": conditioning_id, "outputs": output_ids,
                      "digest": digest, "dir": case_dir, "encode_path": encode_path})
    controller = Path(__file__).with_name("run_repair_batch.py")

    def run(phase, paths, subdirectory=None):
        phase_out = out / phase
        if subdirectory:
            phase_out /= subdirectory
        command = [sys.executable, str(controller), "--runtime", str(args.runtime.resolve()),
                        "--workflow", *map(str, paths), "--out", str(phase_out), "--profile",
                        args.encoding_profile if phase == "encoding" else ("cpu-only" if phase == "decoding" else args.sampling_profile),
                        "--int8-fallback", "--timeout", str(args.timeout)]
        if phase == "encoding" and args.gpu_chunked_logits:
            command.append("--gpu-chunked-logits")
        if phase == "sampling":
            command.extend("--extra-arg=" + value for value in args.sample_extra_arg)
        if phase == "encoding":
            command.extend("--extra-arg=" + value for value in args.encode_extra_arg)
        if args.model_paths:
            command.extend(["--model-paths", str(args.model_paths.resolve())])
        if args.python_executable:
            command.extend(["--python-executable", str(args.python_executable.resolve())])
        subprocess.run(command, check=True)

    if not args.resume_encoding:
        run("encoding", [spec["encode_path"] for spec in specs])
    encoding_source = args.resume_encoding.resolve() if args.resume_encoding else out
    if args.resume_encoding:
        source_summary = json.loads((encoding_source / "encoding/summary.json").read_text(encoding="utf-8"))
        if not source_summary.get("server_stopped"):
            raise ValueError("Source encoding process must have exited before conditions are reused")
    sampling_paths = []
    for spec in specs:
        source_case = encoding_source / "encoding/cases" / spec["label"]
        if args.resume_encoding:
            old_graph = json.loads((source_case / "api.json").read_text(encoding="utf-8"))
            new_graph = json.loads(spec["encode_path"].read_text(encoding="utf-8"))
            if conditioning_signature(old_graph) != conditioning_signature(new_graph):
                raise ValueError(f"Encoding changed for {spec['label']}; refusing condition reuse")
        history = json.loads((source_case / "history.json").read_text(encoding="utf-8"))
        entry = next(iter(history.values()))
        if entry["status"]["status_str"] != "success":
            raise ValueError("Only successfully encoded archives may be reused")
        verified_inputs = []
        if args.resume_encoding:
            # Older runs did not snapshot input hashes. Fail closed if any input
            # was modified after encoding began, and record hashes at reuse.
            timestamps = [payload["timestamp"] for event, payload in entry["status"].get("messages", [])
                          if event == "execution_start" and "timestamp" in payload]
            if not timestamps:
                raise ValueError("Source execution timestamp missing; re-encode")
            input_root = (args.runtime.resolve() / "ComfyUI/input").resolve()
            for node in old_graph.values():
                if node["class_type"] == "LoadImage":
                    name = node["inputs"]["image"]
                    path = (input_root / name).resolve()
                    if not path.is_relative_to(input_root) or path.stat().st_mtime * 1000 > min(timestamps):
                        raise ValueError("Input modified since encoding; refusing archive reuse")
                    verified_inputs.append({"file": name, "sha256_at_reuse": hashlib.sha256(path.read_bytes()).hexdigest(),
                                            "mtime_ns": path.stat().st_mtime_ns})
        relative = entry["outputs"]["repair_save_conditions"]["text"][0]
        archive = args.runtime.resolve() / "ComfyUI/input" / relative
        archive_hash = hashlib.sha256(archive.read_bytes()).hexdigest()
        expected_hash = entry["outputs"]["repair_save_conditions"]["archive_sha256"][0]
        if archive_hash != expected_hash:
            raise ValueError("Encoded conditioning archive changed")
        sampling = copy.deepcopy(spec["graph"])
        sampling["repair_load_conditions"] = {"class_type": "LoadRepairConditioning", "inputs": {
            "file": relative, "expected_sha256": archive_hash}}
        for name, slot in (("positive", 0), ("negative", 1)):
            sampling[spec["conditioning"]]["inputs"][name] = ["repair_load_conditions", slot]
        sampling[spec["sampler"]]["inputs"]["latent_image"] = ["repair_load_conditions", 2]
        sampling_path = spec["dir"] / (spec["label"] + "-sample.api.json")
        sample_graph = latent_sampling_graph(sampling, spec["sampler"], spec["label"], spec["digest"]) if args.isolate_decode else prune(sampling, spec["outputs"])
        sampling_path.write_text(json.dumps(sample_graph, indent=2, ensure_ascii=False), encoding="utf-8")
        (spec["dir"] / "phase-link.json").write_text(json.dumps({"workflow_sha256": spec["digest"],
            "archive_sha256": archive_hash, "archive_file": relative, "encoding_process_exited_before_sampling": True,
            "encoding_reused": bool(args.resume_encoding), "qwen_cache_device_override": args.qwen_cache_device,
            "encoding_api_sha256": hashlib.sha256((source_case / "api.json").read_bytes()).hexdigest(),
            "encoding_history_sha256": hashlib.sha256((source_case / "history.json").read_bytes()).hexdigest(),
            "inputs_checked_at_reuse": verified_inputs,
            "input_check_method": "filesystem mtime predates execution; hashes recorded at reuse" if args.resume_encoding else None}, indent=2), encoding="utf-8")
        sampling_paths.append(sampling_path)
    sample_sources = {}
    if args.isolate_sampling or args.isolate_decode:
        for path in sampling_paths:
            label = path.stem.removesuffix(".api")
            if args.resume_sampling:
                source = args.resume_sampling.resolve() / "sampling" / label
                summary_path = source / "summary.json"
                if summary_path.exists():
                    summary = json.loads(summary_path.read_text(encoding="utf-8"))
                    if summary.get("status") == "execution_pass_visual_review_pending" and summary.get("server_stopped"):
                        actual = json.loads((source / "cases" / label / "api.json").read_text(encoding="utf-8"))
                        if sampling_signature(actual) != sampling_signature(json.loads(path.read_text(encoding="utf-8"))):
                            raise ValueError("Sampling graph changed; refusing sampled latent reuse")
                        sample_sources[label] = source
                        continue
            run("sampling", [path], label)
            sample_sources[label] = out / "sampling" / label
    else:
        run("sampling", sampling_paths)
    if args.isolate_decode:
        for spec, path in zip(specs, sampling_paths):
            sample_label = path.stem.removesuffix(".api")
            source = sample_sources[sample_label]
            summary = json.loads((source / "summary.json").read_text(encoding="utf-8"))
            if not summary.get("server_stopped"):
                raise ValueError("Sampling process must exit before decoding")
            sample_case = source / "cases" / sample_label
            evidence = spec["dir"] / "sampling-evidence"
            evidence.mkdir()
            for name in ("api.json", "history.json", "result.json"):
                shutil.copyfile(sample_case / name, evidence / name)
            history = json.loads((sample_case / "history.json").read_text(encoding="utf-8"))
            entry = next(iter(history.values()))
            if entry["status"]["status_str"] != "success":
                raise ValueError("Sampling did not succeed")
            saved = entry["outputs"]["repair_save_latent"]
            relative, digest = saved["text"][0], saved["archive_sha256"][0]
            archive = args.runtime.resolve() / "ComfyUI/input" / relative
            if hashlib.sha256(archive.read_bytes()).hexdigest() != digest:
                raise ValueError("Sampled latent archive changed")
            decode = latent_decode_graph(spec["graph"], spec["sampler"], spec["outputs"], relative, digest)
            decode_path = spec["dir"] / (spec["label"] + "-decode.api.json")
            decode_path.write_text(json.dumps(decode, indent=2, ensure_ascii=False), encoding="utf-8")
            link_path = spec["dir"] / "phase-link.json"
            link = json.loads(link_path.read_text(encoding="utf-8"))
            link.update({"sampled_latent_file": relative, "sampled_latent_sha256": digest,
                         "sampling_reused": not source.is_relative_to(out),
                         "sampling_source_workflow_sha256": entry["prompt"][2]["repair_save_latent"]["inputs"]["workflow_sha256"],
                         "sampling_process_exited_before_decoding": True,
                         "sampling_api_sha256": hashlib.sha256((sample_case / "api.json").read_bytes()).hexdigest(),
                         "sampling_history_sha256": hashlib.sha256((sample_case / "history.json").read_bytes()).hexdigest()})
            link_path.write_text(json.dumps(link, indent=2), encoding="utf-8")
            run("decoding", [decode_path], spec["label"])
    print("STAGED EXECUTION COMPLETE; visual review still required", flush=True)


if __name__ == "__main__":
    main()
