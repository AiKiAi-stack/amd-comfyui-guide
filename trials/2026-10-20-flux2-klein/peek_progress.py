"""Small disk-backed observer for active Klein cases, probe and server logs."""
import argparse
import json
from pathlib import Path
import psutil

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
p=argparse.ArgumentParser()
p.add_argument('--case',action='append',default=[])
a=p.parse_args()
print('HOST_AVAILABLE_GIB',round(psutil.virtual_memory().available/2**30,2))
probe=sorted((HERE/'gpu-probes').glob('*/result.json'))[-1]
latest_dir=sorted((HERE/'gpu-probes').iterdir())[-1]
print('LATEST_PROBE_DIR',str(latest_dir))
for filename in ['result.json','stdout.log']:
    path=latest_dir/filename
    if path.exists(): print(filename,path.read_text(encoding='utf-8',errors='replace')[-1800:])
for name in a.case:
    assert '/' not in name and '\\' not in name
    folder=HERE/'cases'/name
    result=folder/'result.json'
    if result.exists():
        data=json.loads(result.read_text(encoding='utf-8'))
        print(json.dumps({k:data.get(k) for k in ['id','status','elapsed_seconds','images','error','output_validation_status','observed_peak_host_ram_used_bytes','observed_peak_vram_used_bytes']},ensure_ascii=False))
    elif (folder/'resource-samples.jsonl').exists():
        try: print(name,json.loads((folder/'resource-samples.jsonl').read_text(encoding='utf-8').splitlines()[-1]))
        except (json.JSONDecodeError,IndexError): print(name,'Resource sample write in progress')
    elif (folder/'resource-samples.json').exists():
        try: print(name,json.dumps(json.loads((folder/'resource-samples.json').read_text(encoding='utf-8'))[-1],ensure_ascii=False))
        except json.JSONDecodeError: print(name,'Resource sample write in progress')
    elif (folder/'submission.json').exists(): print(name,'Submitted, no terminal result')
    else: print(name,'Not submitted')
logs=list((ROOT/'trials/2026-10-19-features').glob('server-flux2-klein-nvme*.stderr.log'))
log=max(logs,key=lambda p:p.stat().st_mtime) if logs else None
if log is not None:
    text=log.read_text(encoding='utf-8',errors='replace')
    print('SERVER_LOG',str(log), '\n'.join(text.splitlines()[-12:]))
