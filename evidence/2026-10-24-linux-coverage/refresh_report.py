"""Publish completed attempts while this turn's owned validation is active."""
import argparse
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('controller', type=int)
args = parser.parse_args()
last = None
while not (HERE / 'refresh.stop').exists():
    command = Path('/proc') / str(args.controller) / 'cmdline'
    active = command.exists() and b'run_linux_coverage.py' in command.read_bytes()
    files = [p for p in [*HERE.glob('cases/*/execution.json'), *HERE.glob('cases/*/review.json')] if '--' not in p.parent.name]
    signature = tuple(sorted((str(p), p.stat().st_mtime_ns) for p in files))
    if signature != last:
        subprocess.run([sys.executable, 'scripts/build_workflow_library.py', '--snapshot', 'runtime/ubuntu/object-info-after-keke.json'], cwd=ROOT, check=True)
        subprocess.run([sys.executable, 'scripts/build_platform_report.py'], cwd=ROOT, check=True)
        last = signature
    if not active: break
    time.sleep(10)
