"""Run independent repair workflows sequentially in an owned, recorded service."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.request import Request, urlopen

import psutil


def available_commit():
    """Windows commit headroom, distinct from physical available RAM."""
    if os.name != "nt":
        return None
    import ctypes

    class MemoryStatus(ctypes.Structure):
        _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [
            (name, ctypes.c_ulonglong) for name in ("total_phys", "available_phys", "total_pagefile",
                "available_pagefile", "total_virtual", "available_virtual", "available_extended")]
    status = MemoryStatus()
    status.length = ctypes.sizeof(status)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        raise ctypes.WinError()
    return status.available_pagefile


def stop_tree(pid):
    try:
        process = psutil.Process(pid)
        children = process.children(recursive=True)
    except psutil.NoSuchProcess:
        return
    for child in reversed(children):
        try:
            child.terminate()
        except psutil.NoSuchProcess:
            pass
    try:
        process.terminate()
    except psutil.NoSuchProcess:
        pass
    _, alive = psutil.wait_procs([process, *children], timeout=15)
    for process in alive:
        try:
            process.kill()
        except psutil.NoSuchProcess:
            pass


def unload_owned_models(url, server, timeout=30):
    """Exercise ComfyUI's real /free path and require observed GPU memory release."""
    def stats():
        with urlopen(url + '/system_stats', timeout=3) as response:
            return json.load(response)

    before = stats()
    request = Request(url + '/free', data=json.dumps({
        'unload_models': True, 'free_memory': True}).encode(),
        headers={'Content-Type': 'application/json'})
    with urlopen(request, timeout=3) as response:
        if response.status != 200:
            raise RuntimeError('Owned service rejected unload request')
    deadline = time.monotonic() + timeout
    while True:
        if server.poll() is not None:
            raise RuntimeError(f'Service exited during explicit model unload: {server.returncode}')
        after = stats()
        gpu = [device for device in after['devices'] if device['type'] != 'cpu']
        if gpu and all(device['torch_vram_total'] <= 256 * 1024**2 for device in gpu):
            return {'before': before['devices'], 'after': after['devices'],
                    'gpu_reserved_below_256_mib': True,
                    'meaning': 'Real /free requested; observed allocator memory release, not OOM recovery proof'}
        if time.monotonic() >= deadline:
            raise TimeoutError('Explicit unload requested but GPU memory release was not observed')
        time.sleep(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--workflow", type=Path, nargs="+", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--profile", choices=["cpu-only", "cpu-text", "gpu-text", "gpu-text-dynamic", "kroma", "flux2"], required=True)
    parser.add_argument("--python-executable", type=Path,
                        help="Optional existing runtime interpreter, for example an SSD mirror")
    parser.add_argument("--model-paths", type=Path)
    parser.add_argument("--chunked-logits", action="store_true")
    parser.add_argument("--gpu-chunked-logits", action="store_true")
    parser.add_argument("--int8-fallback", action="store_true")
    parser.add_argument("--timeout", type=int, default=1200)
    parser.add_argument("--port", type=int, default=8190)
    parser.add_argument("--min-commit-mib", type=int, default=1024,
                        help="Stop the owned trial before Windows commit is exhausted; 0 disables the guard")
    parser.add_argument("--extra-arg", action="append", default=[])
    parser.add_argument("--unload-between", action="store_true",
                        help="Exercise /free after every successful case and require GPU allocator release")
    args = parser.parse_args()
    runtime, out = args.runtime.resolve(), args.out.resolve()
    url = f"http://127.0.0.1:{args.port}"
    try:
        urlopen(url + "/system_stats", timeout=3)
    except OSError:
        pass
    else:
        parser.error("Trial port is already occupied; refusing to use or stop another service")
    out.mkdir(parents=True, exist_ok=False)
    env = os.environ.copy()
    for key in ("BARELY_COMFY_CHUNKED_CPU_LOGITS", "BARELY_COMFY_CHUNKED_GPU_LOGITS", "COMFY_GFX1032_INT8_FALLBACK"):
        env.pop(key, None)
    env["PYTHONFAULTHANDLER"] = "1"
    if args.chunked_logits or args.gpu_chunked_logits:
        env["BARELY_COMFY_CHUNKED_CPU_LOGITS"] = "1"
    if args.gpu_chunked_logits:
        env["BARELY_COMFY_CHUNKED_GPU_LOGITS"] = "1"
    if args.int8_fallback:
        env["COMFY_GFX1032_INT8_FALLBACK"] = "1"
    command = [str(args.python_executable.resolve() if args.python_executable else runtime / ".venv/Scripts/python.exe"), "-u", "ComfyUI/main.py",
               "--listen", "127.0.0.1", "--port", str(args.port), "--cpu-vae",
               "--disable-async-offload", "--fast-disk", "--output-directory", str(out / "images")]
    if args.profile == "cpu-only":
        command += ["--cpu", "--disable-dynamic-vram"]
    elif args.profile == "cpu-text":
        command += ["--disable-dynamic-vram", "--lowvram"]
    elif args.profile in {"gpu-text", "kroma"}:
        command += ["--disable-dynamic-vram", "--reserve-vram", "1.0", "--use-split-cross-attention"]
        if args.profile == "kroma":
            command.append("--force-upcast-attention")
    elif args.profile == "gpu-text-dynamic":
        command += ["--enable-dynamic-vram", "--reserve-vram", "1.0", "--use-split-cross-attention"]
    else:
        command += ["--enable-dynamic-vram", "--reserve-vram", "2.0", "--fp8_e4m3fn-text-enc",
                    "--use-split-cross-attention"]
    if args.model_paths:
        command += ["--extra-model-paths-config", str(args.model_paths.resolve())]
    command += args.extra_arg
    summary = {"status": "running", "command": command, "profile": args.profile,
               "min_commit_mib": args.min_commit_mib,
               "explicit_unload_after_each_case": args.unload_between,
               "chunked_logits": args.chunked_logits or args.gpu_chunked_logits,
               "gpu_chunked_logits": args.gpu_chunked_logits, "int8_fallback": args.int8_fallback, "cases": []}

    def save():
        (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    with (out / "server.stdout.log").open("wb") as stdout, (out / "server.stderr.log").open("wb") as stderr:
        server = subprocess.Popen(command, cwd=runtime, env=env, stdout=stdout, stderr=stderr,
                                  creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    summary["pid"] = server.pid
    save()
    active_child = None
    try:
        deadline = time.monotonic() + 600
        while True:
            if server.poll() is not None:
                raise RuntimeError(f"Service startup exit {server.returncode}")
            try:
                with urlopen(url + "/system_stats", timeout=3) as response:
                    summary["system_stats"] = json.load(response)
                break
            except OSError:
                if time.monotonic() > deadline:
                    raise TimeoutError("Service startup timeout")
                time.sleep(2)
        print("READY", server.pid, args.profile, flush=True)
        for workflow in args.workflow:
            label = workflow.stem.removesuffix(".api")
            started = time.monotonic()
            summary["active_case"] = label
            save()
            with (out / f"{label}.stdout.log").open("wb") as stdout, (out / f"{label}.stderr.log").open("wb") as stderr:
                active_child = subprocess.Popen([sys.executable, str(Path(__file__).with_name("replay_workflow.py")),
                    str(workflow.resolve()), "--url", url, "--out", str(out / "cases" / label), "--timeout", str(args.timeout)],
                    stdout=stdout, stderr=stderr, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            print("RUN", label, flush=True)
            with (out / "memory.jsonl").open("a", encoding="utf-8") as memory:
                while active_child.poll() is None:
                    if server.poll() is not None:
                        stop_tree(active_child.pid)
                        raise RuntimeError(f"Service exited during {label}: {server.returncode}; inspect logs for cause")
                    try:
                        process = psutil.Process(server.pid)
                        parts = [process, *process.children(recursive=True)]
                        commit = available_commit()
                        memory.write(json.dumps({"time": time.time(), "case": label,
                            "rss": sum(part.memory_info().rss for part in parts),
                            "host_available": psutil.virtual_memory().available,
                            "commit_available": commit}) + "\n")
                        memory.flush()
                        if commit is not None and args.min_commit_mib > 0 and commit < args.min_commit_mib * 1024**2:
                            summary["operator_stop"] = "automatic_commit_guard"
                            raise MemoryError("Commit guard stopped the owned trial; inspect retained logs for earlier errors")
                    except psutil.NoSuchProcess:
                        pass
                    if time.monotonic() - started > args.timeout + 90:
                        stop_tree(active_child.pid)
                        raise TimeoutError(f"Replay controller timeout for {label}")
                    time.sleep(2)
            summary["cases"].append({"id": label, "exit_code": active_child.returncode,
                                      "seconds": round(time.monotonic() - started, 2)})
            summary.pop("active_case", None)
            save()
            print("DONE", label, active_child.returncode, flush=True)
            if active_child.returncode != 0:
                raise RuntimeError(f"Replay failed for {label}; see retained logs/history")
            if args.unload_between:
                summary['active_unload'] = label
                save()
                evidence = unload_owned_models(url, server)
                summary['cases'][-1]['explicit_unload'] = evidence
                summary.pop('active_unload', None)
                save()
                print('UNLOADED', label, flush=True)
        summary["status"] = "execution_pass_visual_review_pending"
    except (Exception, KeyboardInterrupt) as error:
        summary["status"] = "failed"
        summary["error"] = str(error)
        summary["server_exit_code"] = server.poll()
        print("FAIL", error, flush=True)
    finally:
        if active_child is not None and active_child.poll() is None:
            stop_tree(active_child.pid)
        stop_tree(server.pid)
        server.wait(timeout=20)
        summary["server_stopped"] = True
        summary["final_server_exit_code"] = server.returncode
        retained_log = (out / "server.stderr.log").read_text(encoding="utf-8", errors="replace")
        summary["native_exception_observed"] = any(marker in retained_log for marker in (
            "Windows fatal exception:", "Fatal Python error:"))
        summary["oom_observed"] = "OutOfMemoryError" in retained_log or "Got an OOM" in retained_log
        save()
    return 0 if summary["status"] == "execution_pass_visual_review_pending" else 1


if __name__ == "__main__":
    raise SystemExit(main())
