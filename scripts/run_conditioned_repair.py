"""Encode and sample a KSampler repair in separate processes, retaining exact conditions."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys


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
    parser.add_argument("--encoding-profile", choices=["gpu-text", "gpu-text-dynamic", "cpu-text"], default="gpu-text")
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    specs = []
    for workflow in args.workflow:
        label = workflow.stem.removesuffix(".api")
        if any(spec["label"] == label for spec in specs):
            parser.error("Workflow basenames must be unique")
        graph = json.loads(workflow.read_text(encoding="utf-8"))
        sampler_ids = [k for k, n in graph.items() if n["class_type"] == "KSampler"]
        output_ids = [k for k, n in graph.items() if n["class_type"] == "SaveImage"]
        if len(sampler_ids) != 1 or not output_ids:
            parser.error("Use independent workflows, each with one KSampler and at least one SaveImage")
        sampler_id = sampler_ids[0]
        digest = hashlib.sha256(workflow.read_bytes()).hexdigest()
        encode = copy.deepcopy(graph)
        inputs = graph[sampler_id]["inputs"]
        encode["repair_save_conditions"] = {"class_type": "SaveRepairConditioning", "inputs": {
            "positive": inputs["positive"], "negative": inputs["negative"], "latent": inputs["latent_image"],
            "prefix": label, "workflow_sha256": digest}}
        case_dir = out / "graphs" / label
        case_dir.mkdir(parents=True)
        encode_path = case_dir / (label + ".api.json")
        encode_path.write_text(json.dumps(prune(encode, ["repair_save_conditions"]), indent=2, ensure_ascii=False), encoding="utf-8")
        (case_dir / "original.json").write_bytes(workflow.read_bytes())
        specs.append({"label": label, "graph": graph, "sampler": sampler_id, "outputs": output_ids,
                      "digest": digest, "dir": case_dir, "encode_path": encode_path})
    controller = Path(__file__).with_name("run_repair_batch.py")

    def run(phase, paths):
        command = [sys.executable, str(controller), "--runtime", str(args.runtime.resolve()),
                        "--workflow", *map(str, paths), "--out", str(out / phase), "--profile",
                        args.encoding_profile if phase == "encoding" else "gpu-text",
                        "--int8-fallback", "--timeout", str(args.timeout)]
        if phase == "encoding" and args.gpu_chunked_logits:
            command.append("--gpu-chunked-logits")
        if phase == "sampling":
            command.extend("--extra-arg=" + value for value in args.sample_extra_arg)
        if phase == "encoding":
            command.extend("--extra-arg=" + value for value in args.encode_extra_arg)
        if args.model_paths:
            command.extend(["--model-paths", str(args.model_paths.resolve())])
        subprocess.run(command, check=True)

    run("encoding", [spec["encode_path"] for spec in specs])
    sampling_paths = []
    for spec in specs:
        history = json.loads((out / "encoding/cases" / spec["label"] / "history.json").read_text(encoding="utf-8"))
        entry = next(iter(history.values()))
        relative = entry["outputs"]["repair_save_conditions"]["text"][0]
        archive = args.runtime.resolve() / "ComfyUI/input" / relative
        archive_hash = hashlib.sha256(archive.read_bytes()).hexdigest()
        sampling = copy.deepcopy(spec["graph"])
        sampling["repair_load_conditions"] = {"class_type": "LoadRepairConditioning", "inputs": {
            "file": relative, "expected_sha256": archive_hash}}
        for name, slot in (("positive", 0), ("negative", 1), ("latent_image", 2)):
            sampling[spec["sampler"]]["inputs"][name] = ["repair_load_conditions", slot]
        sampling_path = spec["dir"] / (spec["label"] + "-sample.api.json")
        sampling_path.write_text(json.dumps(prune(sampling, spec["outputs"]), indent=2, ensure_ascii=False), encoding="utf-8")
        (spec["dir"] / "phase-link.json").write_text(json.dumps({"workflow_sha256": spec["digest"],
            "archive_sha256": archive_hash, "archive_file": relative, "encoding_process_exited_before_sampling": True}, indent=2), encoding="utf-8")
        sampling_paths.append(sampling_path)
    run("sampling", sampling_paths)
    print("STAGED EXECUTION COMPLETE; visual review still required", flush=True)


if __name__ == "__main__":
    main()
