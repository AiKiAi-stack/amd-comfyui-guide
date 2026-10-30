"""Stop only the verified owned, interrupted baseline under RAM pressure."""
import json
import time
from datetime import datetime,timezone
from pathlib import Path
import psutil
import requests

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
case_id='zimage-gguf-photo'
folder=HERE/'cases'/case_id
submission=json.loads((folder/'submission.json').read_text(encoding='utf-8'))
assert (folder/'interruption-request.json').exists()
queue=requests.get('http://127.0.0.1:8188/queue',timeout=15).json()
if not queue['queue_running']:
    print('Prompt already ended; nothing forcibly stopped.')
    raise SystemExit(0)
assert len(queue['queue_running'])==1 and not queue['queue_pending']
assert queue['queue_running'][0][1]==submission['prompt_id']
owner=psutil.Process(int((ROOT/'trials/2026-10-19-features/server-zimage.pid').read_text().strip()))
targets=[]
for proc in [owner]+owner.children(recursive=True):
    argv=proc.cmdline()
    if Path(proc.cwd()).resolve()==ROOT and any(a.replace('\\','/').endswith('ComfyUI/main.py') for a in argv):
        targets.append(proc)
assert targets
record=dict(timestamp=datetime.now(timezone.utc).isoformat(),prompt_id=submission['prompt_id'],
            status='operator_stopped_no_output',reason='API interrupt requested but model load did not return; host available RAM fell below 0.5GB. Stop owned service to release memory before independent GPU-text trial.',
            server_processes=[{'pid':p.pid,'argv':p.cmdline(),'created':p.create_time()} for p in targets],queue_before=queue)
path=folder/'operator-stop.json'
path.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
for proc in reversed(targets):
    try: proc.terminate()
    except psutil.NoSuchProcess: pass
_,alive=psutil.wait_procs(targets,timeout=10)
for proc in alive: proc.kill()
psutil.wait_procs(alive,timeout=5)
# The exact case runner has no terminal history to receive after its owned server
# was stopped; terminate only its process chain from this workspace.
runners=[]
for proc in psutil.process_iter(['name']):
    if proc.info['name']!='python.exe': continue
    try:
        argv=proc.cmdline()
        if Path(proc.cwd()).resolve()==ROOT and '--case' in argv and case_id in argv and any(a.replace('\\','/').endswith('2026-10-20-zimage/run_trials.py') for a in argv):
            runners.append(proc)
    except (psutil.NoSuchProcess,psutil.AccessDenied): pass
for proc in sorted(runners,key=lambda p:len(p.parents()),reverse=True):
    try: proc.terminate()
    except psutil.NoSuchProcess: pass
psutil.wait_procs(runners,timeout=5)
record.update(server_stopped=True,runner_pids=[p.pid for p in runners],available_ram_after=psutil.virtual_memory().available)
path.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in record.items() if k not in ('queue_before','server_processes')},indent=2))
