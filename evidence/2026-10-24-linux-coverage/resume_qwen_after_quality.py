"""Continue this turn's explicitly bounded queue after its owned predecessor exits."""
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
TRIAL = Path(__file__).resolve().parent
predecessor = Path('/proc/145661/cmdline')
while predecessor.exists() and b'scripts/run_linux_coverage.py' in predecessor.read_bytes():
    time.sleep(2)
plan = json.loads((TRIAL/'plan.json').read_text())
selected = [c['case_id'] for c in plan if c['model_id'] in ('qwen-base','qwen-turbo')
            and not c.get('superseded_by') and not (TRIAL/'cases'/c['case_id']/'execution.json').exists()]
if not selected:
    raise SystemExit(0)
command = [str(ROOT/'runtime/ubuntu/.venv/bin/python'), '-u', 'scripts/run_linux_coverage.py',
           '--staged', '--timeout', '420', '--cases', *selected]
with (ROOT/'runs/linux-coverage-20261024/qwen-pending.log').open('w') as log:
    child = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    print(json.dumps({'pid':child.pid,'cases':selected}),flush=True)
    with (ROOT/'runs/linux-coverage-20261024/report-refresh-qwen.log').open('w') as refreshlog:
        refresher=subprocess.Popen([sys.executable,str(TRIAL/'refresh_report.py'),str(child.pid)],cwd=ROOT,stdout=refreshlog,stderr=subprocess.STDOUT)
        code=child.wait()
        refresher.wait(timeout=30)
    raise SystemExit(code)
