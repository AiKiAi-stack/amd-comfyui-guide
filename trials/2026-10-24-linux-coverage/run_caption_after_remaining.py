"""Finish the three-stage auxiliary caption case after the owned image queue."""
from pathlib import Path
import subprocess
import sys
import time
p=Path('/proc/17069/cmdline')
while p.exists() and b'scripts/run_linux_coverage.py' in p.read_bytes():time.sleep(2)
with open('runs/linux-coverage-20261024/three-phase-caption.log','w') as log:
 child=subprocess.Popen([sys.executable,'-u','scripts/run_linux_coverage.py','--staged','--pending-only','--timeout','600','--cases','qwen-caption-4b-aux-8b-cpu-staged'],stdout=log,stderr=subprocess.STDOUT)
 print('CAPTION_CONTROLLER_PID',child.pid,flush=True)
 with open('runs/linux-coverage-20261024/report-refresh-three-phase.log','w') as refreshlog:
  subprocess.Popen([sys.executable,'trials/2026-10-24-linux-coverage/refresh_report.py',str(child.pid)],stdout=refreshlog,stderr=subprocess.STDOUT)
 sys.exit(child.wait())
