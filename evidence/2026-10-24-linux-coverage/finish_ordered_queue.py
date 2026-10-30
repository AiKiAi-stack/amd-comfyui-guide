"""After the owned BFS case, prioritize the caption candidate, then finish images."""
import json
from pathlib import Path
import subprocess
import sys
import time
import psutil

ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
completed=HERE/'cases/qwen-bfs-head-swap-stage-nobacking-cpu-encode/execution.json'
while not completed.exists():
    if not psutil.pid_exists(12172):raise RuntimeError('Predecessor ended before BFS result; inspect before resuming')
    time.sleep(1)
parent=psutil.Process(12172)
if 'scripts/run_linux_coverage.py' not in parent.cmdline():raise RuntimeError('Predecessor PID ownership changed')
children=parent.children(recursive=True);parent.terminate()
for child in children:
    try:child.terminate()
    except psutil.NoSuchProcess:pass
_,alive=psutil.wait_procs([parent,*children],timeout=10)
for child in alive:child.kill()
(HERE/'ordered-queue-handoff.json').write_text(json.dumps({'time':time.time(),'completed_before_stop':str(completed),'stopped_controller':12172,'owned_descendants':[p.pid for p in children],'reason':'Preserve completed BFS result; prioritize GPU caption and finish the remaining bounded cases'},indent=2)+'\n')
cases=['qwen-caption-gpu-bf16-backing-v4','flux2-teapot-structure-linux-repair','turbo-fox-profile-wide-mask-linux-repair-cpu-encode','turbo-un-face-swap-stage-nobacking-bf16-te-cpu-encode','turbo-un-role-replacement-test-stage-nobacking-bf16-te-cpu-encode']
for case in cases:
    print('ORDERED_CASE',case,flush=True)
    with (ROOT/'runs/linux-coverage-20261024'/('final-'+case+'.log')).open('a') as log:
        child=subprocess.Popen([sys.executable,'-u','scripts/run_linux_coverage.py','--staged','--pending-only','--timeout','600','--cases',case],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        with (ROOT/'runs/linux-coverage-20261024'/('refresh-final-'+case+'.log')).open('w') as refreshlog:
            refresher=subprocess.Popen([sys.executable,str(HERE/'refresh_report.py'),str(child.pid)],cwd=ROOT,stdout=refreshlog,stderr=subprocess.STDOUT)
            code=child.wait();refresher.wait(timeout=45)
    if code:raise RuntimeError(f'Controller failed for {case}: {code}')
print('ORDERED_QUEUE_FINISHED',flush=True)
