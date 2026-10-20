"""Read concise progress without loading a PowerShell or torch observer."""
import argparse
import json
from pathlib import Path
import psutil
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
p=argparse.ArgumentParser()
p.add_argument('--case',action='append',required=True)
a=p.parse_args()
for name in a.case:
    assert '/' not in name and '\\' not in name
    folder=HERE/'cases'/name
    pidfile=ROOT/'trials/2026-10-19-features'/f'server-isolated-{name}.pid'
    if pidfile.exists():
        try:
            parent=psutil.Process(int(pidfile.read_text().strip()))
            processes=[parent]+parent.children(recursive=True)
            states=[]
            for process in processes:
                io=process.io_counters()
                states.append(dict(pid=process.pid,rss_bytes=process.memory_info().rss,
                    cpu_seconds=round(sum(process.cpu_times()[:2]),2),read_bytes=io.read_bytes))
            print('OWNED_SERVER',json.dumps(dict(processes=states,host_available_bytes=psutil.virtual_memory().available)))
        except (psutil.NoSuchProcess,psutil.AccessDenied,ValueError):
            print('Owned server process is no longer accessible')
    result=folder/'result.json'
    if result.exists():
        r=json.loads(result.read_text(encoding='utf-8'))
        print(json.dumps({k:r.get(k) for k in ['id','status','elapsed_seconds','images','output_validation_status','observed_peak_host_ram_used_bytes','observed_peak_vram_used_bytes']},ensure_ascii=False))
    elif (folder/'resource-samples.json').exists():
        try:
            samples=json.loads((folder/'resource-samples.json').read_text(encoding='utf-8'))
            print(name, json.dumps(samples[-1],ensure_ascii=False))
        except json.JSONDecodeError: print(name,'Resource sample update in progress')
    else: print(name,'No terminal result or resource samples yet')
    log=ROOT/'trials/2026-10-19-features'/f'server-isolated-{name}.stderr.log'
    if log.exists():
        text=log.read_text(encoding='utf-8',errors='replace')
        if 'Windows fatal exception:' in text:
            text=text[text.index('Windows fatal exception:'):]
            print('\n'.join(text.splitlines()[:16]))
        else: print('\n'.join(text.splitlines()[-8:]))
