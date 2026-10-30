"""Record disk and owned-server I/O deltas without importing torch."""
import json
import time
from datetime import datetime, timezone
from pathlib import Path
import psutil

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def sample():
    records={}
    pidfile=ROOT/'trials/2026-10-19-features/server-isolated-zimage-aio-photo-9step.pid'
    try:
        parent=psutil.Process(int(pidfile.read_text().strip()))
        for p in [parent]+parent.children(recursive=True):
            records[str(p.pid)]=dict(io=p.io_counters()._asdict(),cpu_seconds=sum(p.cpu_times()[:2]),rss=p.memory_info().rss)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
    return dict(at=datetime.now(timezone.utc).isoformat(),disks={k:v._asdict() for k,v in psutil.disk_io_counters(perdisk=True).items()},processes=records,
                host_available=psutil.virtual_memory().available)
first=sample()
time.sleep(5)
last=sample()
out=dict(first=first,last=last)
out['disk_delta']={k:{f:v-last_value.get(f,0) for f,v in value.items()} for k,value in last['disks'].items() if (last_value:=first['disks'].get(k)) is not None}
out['process_delta']={k:dict(read_bytes=v['io']['read_bytes']-first['processes'][k]['io']['read_bytes'],cpu_seconds=v['cpu_seconds']-first['processes'][k]['cpu_seconds']) for k,v in last['processes'].items() if k in first['processes']}
path=HERE/f"startup-io-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.json"
path.write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps(dict(path=str(path),disk_delta=out['disk_delta'],process_delta=out['process_delta'],host_available=last['host_available']),indent=2))
