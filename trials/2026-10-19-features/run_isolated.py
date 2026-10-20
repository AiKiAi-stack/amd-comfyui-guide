"""Run each pending case in a fresh ComfyUI process to contain native crashes."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import shutil
import subprocess

import feature_bench

ROOT = feature_bench.ROOT
HERE = feature_bench.HERE

parser = argparse.ArgumentParser()
parser.add_argument("model", choices=["kroma", "qwen", "turbo-un"])
parser.add_argument("--retry-errors", action="store_true")
parser.add_argument("--case")
parser.add_argument("--cpu-text", action="store_true")
parser.add_argument("--int8-fallback", action="store_true")
args = parser.parse_args()
cases = json.loads((HERE / "cases.json").read_text(encoding="utf-8"))
for case in cases:
    if case["model"] != args.model or (args.case and args.case != case["id"]):
        continue
    case_dir = HERE / "cases" / case["id"]
    result = case_dir / "result.json"
    if result.exists():
        record = json.loads(result.read_text(encoding="utf-8"))
        if record.get("status") == "success" or not args.retry_errors:
            print("SKIP", case["id"], record.get("status"), flush=True)
            continue
        destination = HERE / "attempts" / (case["id"] + "-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
        # Check resolved absolute paths before moving this evidence directory.
        case_dir.resolve().relative_to((HERE / "cases").resolve())
        destination.resolve().relative_to((HERE / "attempts").resolve())
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(case_dir), str(destination))
        print("ARCHIVED", destination, flush=True)
    command = [str(ROOT / ".venv/Scripts/python.exe"), "-u", str(HERE / "manage_server.py"), "restart", "--model", args.model]
    if args.cpu_text:
        command.append("--cpu-text")
    if args.int8_fallback:
        command.append("--int8-fallback")
    subprocess.run(command, cwd=ROOT, check=True)
    try:
        feature_bench.run(case)
    except RuntimeError as error:
        print("Isolated case failed; proceeding after fresh restart:", error, flush=True)
