"""Run two Qwen reload cases with a Linux physical RAM guard around the existing runner."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

import psutil

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from run_repair_batch import stop_tree


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--timeout', type=int, default=1200)
    parser.add_argument('--extra-arg', action='append', default=[])
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists():
        parser.error('Use a fresh output directory')
    out.parent.mkdir(parents=True, exist_ok=True)
    runtime = ROOT / 'runtime/ubuntu'
    workflows = Path(__file__).with_name('workflows')
    command = [sys.executable, str(ROOT / 'scripts/run_repair_batch.py'),
        '--runtime', str(runtime), '--python-executable', str(runtime / '.venv/bin/python'),
        '--model-paths', str(runtime / 'model-paths.yaml'), '--profile', 'gpu-text',
        '--extra-arg=--force-upcast-attention', '--unload-between', '--timeout', str(args.timeout),
        '--workflow', str(workflows / 'qwen-reload-01.api.json'),
        str(workflows / 'qwen-reload-02.api.json'), '--out', str(out)]
    command.extend('--extra-arg=' + value for value in args.extra_arg)
    record = {'command': command, 'guard_mib': 1536, 'operator_stop': False, 'samples': []}
    record_path = out.with_name(out.name + '-ram-guard.json')
    with out.with_name(out.name + '-controller.log').open('wb') as log:
        process = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        try:
            while process.poll() is None:
                available = psutil.virtual_memory().available
                record['samples'].append({'time': time.time(), 'host_available_bytes': available})
                record_path.write_text(json.dumps(record, indent=2) + '\n')
                if available < 1536 * 1024**2:
                    record['operator_stop'] = True
                    stop_tree(process.pid)
                    break
                time.sleep(2)
            process.wait(timeout=30)
        finally:
            if process.poll() is None:
                stop_tree(process.pid)
                process.wait(timeout=30)
            record['controller_exit_code'] = process.returncode
            record_path.write_text(json.dumps(record, indent=2) + '\n')
    return 1 if record['operator_stop'] else process.returncode


if __name__ == '__main__':
    raise SystemExit(main())
