"""Run selected cases serially, refreshing the probe before each stale preflight."""
import argparse
import json
import subprocess
import sys
from datetime import datetime,timezone
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
p=argparse.ArgumentParser()
p.add_argument('--case',action='append',required=True)
a=p.parse_args()
valid={c['id'] for c in json.loads((HERE/'cases.json').read_text(encoding='utf-8'))}
for case_id in a.case:
    assert case_id in valid
    if (HERE/'cases'/case_id/'result.json').exists():
        existing=json.loads((HERE/'cases'/case_id/'result.json').read_text(encoding='utf-8'))
        assert existing.get('status')=='success', 'Recorded failure must be reviewed before continuing a selected batch'
        print('SKIP recorded attempt',case_id,flush=True)
        continue
    probe_dir=sorted((HERE/'gpu-probes').iterdir())[-1]
    probe_path=probe_dir/'result.json'
    probe=json.loads(probe_path.read_text(encoding='utf-8')) if probe_path.exists() else {}
    completed=datetime.fromisoformat(probe['completed_at']) if probe.get('completed_at') else None
    if completed is None or not probe.get('healthy') or not 0<=(datetime.now(timezone.utc)-completed).total_seconds()<240:
        subprocess.run([sys.executable,'-X','utf8','-u',str(HERE/'probe_gpu.py')],cwd=ROOT,check=True)
        probe=json.loads(sorted((HERE/'gpu-probes').glob('*/result.json'))[-1].read_text(encoding='utf-8'))
        assert probe.get('healthy'), 'GPU health failed; stop without driver reset or inference'
    subprocess.run([sys.executable,'-X','utf8','-u',str(HERE/'run_trials.py'),'--case',case_id],cwd=ROOT,check=True)
