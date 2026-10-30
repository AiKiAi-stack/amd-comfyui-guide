"""Contain native GPU failures in a child process and preserve fresh evidence."""
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import psutil

HERE = Path(__file__).resolve().parent
stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
dest = HERE / 'gpu-probes' / stamp
dest.mkdir(parents=True, exist_ok=False)
code = '''print("STAGE torch_import_start", flush=True)
import torch
print("STAGE torch_import_complete", torch.__version__, flush=True)
print(torch.cuda.is_available(), flush=True)
print(torch.cuda.get_device_name(0), flush=True)
print("STAGE memory_query_start", flush=True)
print(torch.cuda.mem_get_info(), flush=True)
print("STAGE small_matmul_start", flush=True)
a = torch.ones((16, 16), device="cuda")
b = a @ a
torch.cuda.synchronize()
print("MATMUL_OK", b[0, 0].item(), flush=True)
'''
start = time.monotonic()
with (dest / 'stdout.log').open('wb') as out, (dest / 'stderr.log').open('wb') as err:
    proc = subprocess.Popen([sys.executable, '-X', 'utf8', '-u', '-c', code], stdout=out, stderr=err)
    timed_out = False
    gpu_started = None
    while proc.poll() is None:
        elapsed = time.monotonic() - start
        progress = (dest / 'stdout.log').read_text(encoding='utf-8', errors='replace')
        if gpu_started is None and 'STAGE torch_import_complete' in progress:
            gpu_started = time.monotonic()
        if (gpu_started is None and elapsed > 300) or (gpu_started is not None and time.monotonic()-gpu_started > 75):
            timed_out = True
            try:
                children = psutil.Process(proc.pid).children(recursive=True)
            except psutil.NoSuchProcess:
                children = []
            for child in reversed(children):
                try:
                    child.kill()
                except psutil.NoSuchProcess:
                    pass
            proc.kill()
            proc.wait()
            psutil.wait_procs(children, timeout=5)
            break
        time.sleep(0.5)
stdout = (dest / 'stdout.log').read_text(encoding='utf-8', errors='replace')
result = dict(timestamp=stamp, boot_time_utc=datetime.fromtimestamp(psutil.boot_time(), timezone.utc).isoformat(),
              completed_at=datetime.now(timezone.utc).isoformat(),
              returncode=proc.returncode, timed_out=timed_out, elapsed_seconds=round(time.monotonic()-start, 2),
              healthy=proc.returncode == 0 and 'MATMUL_OK 16.0' in stdout, stdout=stdout,
              stderr_file=str(dest / 'stderr.log'))
result['status'] = ('healthy' if result['healthy'] else 'inconclusive_import_timeout'
                    if timed_out and 'STAGE torch_import_complete' not in stdout else 'gpu_probe_failed')
result['import_and_launch_seconds'] = round((gpu_started-start) if gpu_started is not None else time.monotonic()-start, 2)
result['gpu_stage_seconds'] = round(time.monotonic()-gpu_started,2) if gpu_started is not None else None
(dest / 'result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps({**result, 'stdout': stdout[:1600]}, indent=2), flush=True)
