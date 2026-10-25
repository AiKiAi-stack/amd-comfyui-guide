"""Exercise changed prompts in ONE owned ComfyUI process; retain every failure."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.error
import urllib.request

import psutil


def api(base, path, payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    request = urllib.request.Request(base + path, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.load(response)


def save(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--runtime", type=Path, required=True)
    p.add_argument("--workflow", type=Path, required=True)
    p.add_argument("--model-paths", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--port", type=int, default=8190)
    p.add_argument("--count", type=int, default=3)
    p.add_argument("--timeout", type=int, default=600)
    p.add_argument("--min-available-ram-mib", type=int, default=0,
                   help="Stop the owned service below this physical RAM headroom; 0 disables")
    p.add_argument("--extra-arg", action="append", default=[])
    args = p.parse_args()
    if args.count < 2:
        p.error("At least two generations are required to test reloads")
    args.runtime = args.runtime.resolve()
    args.out = args.out.resolve()
    template = json.loads(args.workflow.read_text(encoding="utf-8-sig"))
    expected = {"8": "CLIPTextEncode", "10": "KSampler", "18": "SaveImage"}
    if any(template.get(key, {}).get("class_type") != kind for key, kind in expected.items()):
        p.error("Use the tracked Z-Image GGUF fixture: node IDs 8/10/18 are required")
    if "blue ceramic" not in template["8"]["inputs"].get("text", ""):
        p.error("Fixture must contain 'blue ceramic' so every prompt actually changes")
    args.out.mkdir(parents=True, exist_ok=False)
    base = f"http://127.0.0.1:{args.port}"
    try:
        api(base, "/system_stats")
    except (OSError, urllib.error.URLError):
        pass
    else:
        raise RuntimeError("Port already serves ComfyUI; refusing to use another process")
    python = args.runtime / (".venv/Scripts/python.exe" if os.name == "nt" else ".venv/bin/python")
    command = [str(python), "-X", "faulthandler", "-u",
               "ComfyUI/main.py", "--listen", "127.0.0.1", "--port", str(args.port),
               "--cpu-vae", "--disable-async-offload", "--disable-dynamic-vram",
               "--extra-model-paths-config", str(args.model_paths.resolve()),
               "--output-directory", str(args.out / "images"), *args.extra_arg]
    summary = {"status": "running", "command": command, "cases": [], "same_process": True,
               "min_available_ram_mib": args.min_available_ram_mib}
    revisions_file = args.runtime / "source-revisions.json"
    revisions = json.loads(revisions_file.read_text()) if revisions_file.exists() else {}
    for label, directory in (("comfyui", args.runtime / "ComfyUI"),
                             ("gguf", args.runtime / "ComfyUI/custom_nodes/ComfyUI-GGUF")):
        if (directory / ".git").exists():
            revision = subprocess.check_output(
                ["git", "-C", str(directory), "rev-parse", "HEAD"], text=True).strip()
        else:
            key = "ComfyUI" if label == "comfyui" else "ComfyUI-GGUF"
            revision = revisions[key]["commit"]
        summary[label + "_revision"] = revision
    save(args.out / "summary.json", summary)
    env = os.environ.copy()
    env["PYTHONFAULTHANDLER"] = "1"
    with (args.out / "server.stdout.log").open("wb") as stdout, (args.out / "server.stderr.log").open("wb") as stderr:
        process = subprocess.Popen(command, cwd=args.runtime, env=env, stdout=stdout, stderr=stderr,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        summary["pid"] = process.pid
        summary["wall_started"] = time.time()

        def sample():
            try:
                parent = psutil.Process(process.pid)
                rss = sum(p.memory_info().rss for p in [parent, *parent.children(recursive=True)])
                record = {"time": time.time(), "process_tree_rss": rss,
                          "host_available_ram": psutil.virtual_memory().available}
                with (args.out / "memory.jsonl").open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps(record) + "\n")
                if args.min_available_ram_mib > 0 and record["host_available_ram"] < args.min_available_ram_mib * 1024**2:
                    summary["operator_stop"] = "automatic_physical_ram_guard"
                    raise MemoryError("Physical RAM guard stopped the owned trial; not a native crash")
            except psutil.NoSuchProcess:
                pass
        try:
            deadline = time.monotonic() + args.timeout
            while True:
                sample()
                if process.poll() is not None:
                    raise RuntimeError(f"Server died during startup: {process.returncode}")
                try:
                    summary["system_stats"] = api(base, "/system_stats")
                    break
                except (OSError, urllib.error.URLError):
                    if time.monotonic() > deadline:
                        raise TimeoutError("Startup timeout")
                    time.sleep(2)
            print("READY", process.pid, flush=True)
            prompts = ["red", "blue", "green", "yellow", "purple"]
            for index in range(args.count):
                graph = json.loads(json.dumps(template))
                color = prompts[index % len(prompts)]
                graph["8"]["inputs"]["text"] = template["8"]["inputs"]["text"].replace("blue ceramic", f"{color} ceramic")
                graph["10"]["inputs"]["seed"] = template["10"]["inputs"]["seed"] + index
                graph["18"]["inputs"]["filename_prefix"] = f"repeat-{index + 1:02d}-{color}"
                save(args.out / f"workflow-{index + 1:02d}.json", graph)
                started = time.monotonic()
                submission = api(base, "/prompt", {"prompt": graph})
                if submission.get("node_errors"):
                    raise RuntimeError(f"Invalid graph: {submission['node_errors']}")
                prompt_id = submission["prompt_id"]
                case = {"index": index + 1, "color": color, "prompt_id": prompt_id}
                summary["cases"].append(case)
                save(args.out / "summary.json", summary)
                print("SUBMITTED", index + 1, prompt_id, flush=True)
                while True:
                    sample()
                    if process.poll() is not None:
                        raise RuntimeError(f"Native server exit during generation {index + 1}: {process.returncode}")
                    history = api(base, "/history/" + prompt_id)
                    if prompt_id in history:
                        entry = history[prompt_id]
                        save(args.out / f"history-{index + 1:02d}.json", history)
                        case["seconds"] = round(time.monotonic() - started, 2)
                        if entry["status"]["status_str"] != "success":
                            raise RuntimeError(f"Generation {index + 1} failed; see history")
                        cached = [node for event, data in entry["status"].get("messages", [])
                                  if event == "execution_cached" for node in data.get("nodes", [])]
                        if "8" in cached or "10" in cached:
                            raise RuntimeError("Text encoding or sampling was cached; reload trigger not exercised")
                        case["cached_nodes"] = cached
                        from PIL import Image, ImageStat
                        images = []
                        for output in entry["outputs"].values():
                            for image in output.get("images", []):
                                path = args.out / "images" / image["subfolder"] / image["filename"]
                                with Image.open(path) as img:
                                    img.load()
                                    images.append({"file": str(path.relative_to(args.out)), "size": list(img.size),
                                                   "stddev": ImageStat.Stat(img.convert("RGB")).stddev,
                                                   "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
                        if not images:
                            raise RuntimeError("History success without saved images")
                        case["images"] = images
                        case["status"] = "execution_pass_visual_review_pending"
                        print("OUTPUT", index + 1, case["seconds"], flush=True)
                        save(args.out / "summary.json", summary)
                        break
                    if time.monotonic() - started > args.timeout:
                        raise TimeoutError(f"Generation {index + 1} timed out")
                    time.sleep(2)
            summary["status"] = "execution_pass_visual_review_pending"
        except (Exception, KeyboardInterrupt) as error:
            summary["status"] = "interrupted" if isinstance(error, KeyboardInterrupt) else "failed"
            summary["error"] = str(error)
            summary["exit_code"] = process.poll()
            print("FAIL", error, flush=True)
        finally:
            try:
                children = psutil.Process(process.pid).children(recursive=True)
            except psutil.NoSuchProcess:
                children = []
            for child in reversed(children):
                try:
                    child.terminate()
                except psutil.NoSuchProcess:
                    pass
            _, alive = psutil.wait_procs(children, timeout=10)
            for child in alive:
                child.kill()
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=20)
            summary["server_stopped"] = process.poll() is not None
            summary["wall_finished"] = time.time()
            save(args.out / "summary.json", summary)
    return 0 if summary["status"] == "execution_pass_visual_review_pending" else 1


if __name__ == "__main__":
    raise SystemExit(main())
