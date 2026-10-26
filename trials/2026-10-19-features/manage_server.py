import argparse
import json
import os
from pathlib import Path
import subprocess
import time

import psutil
import requests

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def ours():
    found = []
    candidates = {}
    for pidfile in list(HERE.glob("server-*.pid")) + list((ROOT / "trials/2026-10-18").glob("server-*.pid")):
        try:
            parent = psutil.Process(int(pidfile.read_text().strip()))
            for process in [parent] + parent.children(recursive=True):
                candidates[process.pid] = process
        except (ValueError, psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    for process in candidates.values():
        try:
            argv = process.cmdline()
            cwd = Path(process.cwd()).resolve()
            is_main = any(arg.replace("\\", "/").lower().endswith("comfyui/main.py") or arg.lower() == "main.py" for arg in argv)
            if is_main and cwd in (ROOT, ROOT / "ComfyUI"):
                found.append(process)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return found


def status():
    print(json.dumps({"pids": [p.pid for p in ours()], "available_ram_gb": round(psutil.virtual_memory().available / 2**30, 2)}, indent=2), flush=True)
    try:
        queue = requests.get("http://127.0.0.1:8188/queue", timeout=5).json()
        print("queue", len(queue["queue_running"]), len(queue["queue_pending"]), flush=True)
    except requests.RequestException as error:
        print(str(error), flush=True)


def restart(model, cpu_text=False, int8_fallback=False, extra_args=None, fast_disk=True):
    pause_flag = HERE / "stop-kroma-after-materials.flag"
    style_result = HERE / "cases/kroma-style-source/result.json"
    if model == "kroma" and pause_flag.exists() and style_result.exists():
        if json.loads(style_result.read_text(encoding="utf-8")).get("status") == "success":
            raise SystemExit("Materials complete; intentionally stop isolated runner before the reference batch")
    try:
        queue = requests.get("http://127.0.0.1:8188/queue", timeout=5).json()
        if queue["queue_running"] or queue["queue_pending"]:
            raise RuntimeError("Refusing to stop an active ComfyUI queue")
    except requests.ConnectionError:
        pass
    processes = ours()
    print("Stopping workspace ComfyUI pids", [p.pid for p in processes], flush=True)
    # Children are Python venv launch wrappers of this same exact workspace main.py.
    for process in sorted(processes, key=lambda p: p.pid, reverse=True):
        try:
            process.terminate()
        except psutil.NoSuchProcess:
            pass
    psutil.wait_procs(processes, timeout=15)
    env = os.environ.copy()
    env.pop("COMFY_GFX1032_INT8_FALLBACK", None)
    if model == "moss" or int8_fallback:
        env["COMFY_GFX1032_INT8_FALLBACK"] = "1"
    stdout = (HERE / f"server-{model}.stdout.log").open("ab")
    stderr = (HERE / f"server-{model}.stderr.log").open("ab")
    command = [str(ROOT / ".venv/Scripts/python.exe"), "-u", "ComfyUI/main.py", "--listen", "127.0.0.1", "--port", "8188", "--cpu-vae", "--disable-async-offload"]
    if fast_disk:
        command += ["--fast-disk"]
    if cpu_text:
        command += ["--disable-dynamic-vram", "--lowvram"]
    if extra_args:
        command += list(extra_args)
    process = subprocess.Popen(
        command,
        cwd=ROOT, env=env, stdout=stdout, stderr=stderr,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    (HERE / f"server-{model}.pid").write_text(str(process.pid))
    print("Started", process.pid, flush=True)
    # Cold imports can exceed four minutes while large weight files are read on D:.
    deadline = time.monotonic() + 600
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Server exited {process.returncode}; inspect server-{model}.stderr.log")
        try:
            requests.get("http://127.0.0.1:8188/system_stats", timeout=3).raise_for_status()
            print("READY", flush=True)
            return
        except requests.RequestException:
            time.sleep(3)
    raise TimeoutError("Server not ready within 600 seconds")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["status", "restart"])
    parser.add_argument("--model", choices=["moss", "kroma", "qwen", "turbo-un"], default="qwen")
    parser.add_argument("--cpu-text", action="store_true", help="Use legacy LOW_VRAM mode, whose text_encoder_device is CPU")
    parser.add_argument("--int8-fallback", action="store_true", help="Opt in to the existing gfx1032 dequantized matmul fallback")
    args = parser.parse_args()
    if args.action == "status":
        status()
    else:
        restart(args.model, args.cpu_text, args.int8_fallback)
