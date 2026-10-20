"""Run each requested feature in a fresh owned server, preserving native failures."""
import argparse
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime,timezone
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--case',action='append',required=True)
args=parser.parse_args()
definitions={c['id']:c for c in json.loads((HERE/'cases.json').read_text(encoding='utf-8'))}

def fresh_probe(max_age):
    probes=sorted((ROOT/'trials/2026-10-20-flux2-klein/gpu-probes').glob('*/result.json'))
    latest=json.loads(probes[-1].read_text(encoding='utf-8')) if probes else {}
    completed=datetime.fromisoformat(latest['completed_at']) if latest.get('completed_at') else None
    if completed is None or not latest.get('healthy') or (datetime.now(timezone.utc)-completed).total_seconds()>max_age:
        subprocess.run([sys.executable,'-X','utf8','-u',str(ROOT/'trials/2026-10-20-flux2-klein/probe_gpu.py')],cwd=ROOT,check=True)
        latest=json.loads(sorted((ROOT/'trials/2026-10-20-flux2-klein/gpu-probes').glob('*/result.json'))[-1].read_text(encoding='utf-8'))
    assert latest.get('healthy'), 'GPU probe failed: no inference or reset attempted'

for case_id in args.case:
    assert case_id in definitions,case_id
    case=definitions[case_id]
    folder=HERE/'cases'/case_id
    if (folder/'result.json').exists():
        print('SKIP recorded result',case_id,flush=True)
        continue
    assert not (folder/'submission.json').exists(), 'Reconcile existing submission before retry'
    assert case.get('memory_profile') in ('legacy-normalvram', 'dynamic-nvme')
    case_start=time.monotonic()
    case_started_at=datetime.now(timezone.utc).isoformat()
    fresh_probe(900)
    label='isolated-'+case_id
    print('START_FRESH_SERVER',case_id,flush=True)
    startup_start=time.monotonic()
    startup=subprocess.run([sys.executable,'-X','utf8','-u',str(HERE/'start_server.py'),'--profile',case['memory_profile'],'--ssd','--label',label],cwd=ROOT)
    startup_seconds=time.monotonic()-startup_start
    if startup.returncode:
        raise SystemExit('Server startup failed; preserve logs and stop the batch')
    fresh_probe(240)
    print('RUN_ISOLATED_CASE',case_id,flush=True)
    run_start=time.monotonic()
    run=subprocess.run([sys.executable,'-X','utf8','-u',str(HERE/'run_trials.py'),'--case',case_id],cwd=ROOT)
    folder.mkdir(parents=True,exist_ok=True)
    (folder/'isolation-timing.json').write_text(json.dumps(dict(started_at=case_started_at,server_start_seconds=round(startup_seconds,2),
        runner_seconds=round(time.monotonic()-run_start,2),whole_case_seconds=round(time.monotonic()-case_start,2),
        note='Measured orchestration wall time includes startup, health/preflight, model loading, generation and runner. Downloads and SSD mirror preparation excluded.'),indent=2),encoding='utf-8')
    for kind in ['stderr','stdout']:
        source=ROOT/'trials/2026-10-19-features'/f'server-{label}.{kind}.log'
        if source.exists(): shutil.copy2(source,folder/f'server.{kind}.log')
    if run.returncode:
        (folder/'runner-exit.json').write_text(json.dumps(dict(returncode=run.returncode,finished_at=datetime.now(timezone.utc).isoformat(),
            note='Raw API/submission/log evidence retained. No fabricated terminal history or result.'),indent=2),encoding='utf-8')
        raise SystemExit('Case failed; stop before another GPU workload')
    print('FINISHED_ISOLATED_CASE',case_id,flush=True)
    subprocess.run([sys.executable,'-X','utf8',str(HERE/'sync_gallery.py')],cwd=ROOT,check=True)
    subprocess.run([sys.executable,'-X','utf8',str(HERE/'update_status.py')],cwd=ROOT,check=True)
