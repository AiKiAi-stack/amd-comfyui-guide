"""Publish selected repeat-test evidence, keeping raw logs and PNGs under runs/."""
import argparse
import hashlib
import json
from pathlib import Path
import re

from PIL import Image


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    source, target = args.run.resolve(), args.destination.resolve()
    target.mkdir(parents=True, exist_ok=False)
    summary = json.loads((source / "summary.json").read_text(encoding="utf-8"))
    summary["raw_summary_sha256"] = sha(source / "summary.json")
    for case in summary["cases"]:
        index = case["index"]
        workflow = source / f"workflow-{index:02d}.json"
        (target / workflow.name).write_bytes(workflow.read_bytes())
        history = source / f"history-{index:02d}.json"
        if history.exists():
            case["raw_history_sha256"] = sha(history)
            data = json.loads(history.read_text(encoding="utf-8"))[case["prompt_id"]]
            cached = [node for event, payload in data["status"].get("messages", [])
                      if event == "execution_cached" for node in payload.get("nodes", [])]
            case["cached_nodes"] = cached
            case["text_encoding_reran"] = "8" not in cached
            case["sampling_reran"] = "10" not in cached
            assert case["text_encoding_reran"] and case["sampling_reran"], "Reload trigger was skipped"
            # Full originals remain local; publish status/output binding without runtime internals.
            public = {"prompt_id": case["prompt_id"], "status": data["status"]["status_str"],
                      "outputs": data["outputs"]}
            (target / history.name).write_text(json.dumps(public, indent=2), encoding="utf-8")
        for record in case.get("images", []):
            original = source / record["file"]
            published = target / original.name
            with Image.open(original) as image:
                clean = Image.frombytes(image.mode, image.size, image.tobytes())
                clean.save(published)
                with Image.open(published) as check:
                    assert check.mode == image.mode and check.size == image.size
                    assert check.tobytes() == image.tobytes(), "Publication changed pixels"
            record["original_sha256"] = record.pop("sha256")
            record["public_sha256"] = sha(published)
            record["file"] = published.name
            record["pixels_unchanged"] = True
    # Preserve the signal, omit unrelated startup messages and native DLL addresses.
    log = (source / "server.stderr.log").read_text(encoding="utf-8", errors="replace")
    log = re.sub(r"\x1b\[[0-9;]*m", "", log)
    lines = [line for line in log.splitlines() if re.search(
        r"Requested to load|loaded completely|loaded partially|Unloaded partially|Prompt executed|"
        r"fatal exception|Exception Code|in to$|in partially_unload$|in unpatch_model$|Enabled pinned memory", line)]
    summary["log_signal"] = [re.sub(r'File ".*?[/\\]([^/\\"]+\.py)"', r'File "\1"', line) for line in lines]
    # The command is retained, with paths made portable. Workflow and image hashes refer to actual runs.
    command = summary["command"]
    runtime = str(Path(command[0]).parents[2])
    summary["command"] = [part.replace(str(source), "RUN_OUTPUT").replace(runtime, "RUNTIME_ROOT") for part in command]
    if "--extra-model-paths-config" in command:
        i = command.index("--extra-model-paths-config")
        summary["command"][i + 1] = "MODEL_PATHS.yaml"
    if "system_stats" in summary:
        summary["system_stats"]["system"].pop("argv", None)
    summary["published_evidence"] = "Selected status, workflows, pixel-identical PNGs, hashes and log signal. Raw logs/history retained locally."
    (target / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(target)


if __name__ == "__main__":
    main()
