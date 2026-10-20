"""Record model file mappings of the exact workspace-owned active server."""
import json
from datetime import datetime,timezone
from pathlib import Path
import psutil

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
parent=psutil.Process(int((ROOT/'trials/2026-10-19-features/server-zimage-gpu-text.pid').read_text().strip()))
records=[]
for p in [parent]+parent.children(recursive=True):
    if Path(p.cwd()).resolve()!=ROOT or not any(a.replace('\\','/').endswith('ComfyUI/main.py') for a in p.cmdline()): continue
    maps=[m._asdict() for m in p.memory_maps(grouped=True) if m.path.lower().endswith(('.gguf','.safetensors'))]
    records.append({'pid':p.pid,'model_file_mappings':maps})
path=HERE/'active-storage-audits'
path.mkdir(exist_ok=True)
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
(path/(stamp+'.json')).write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(records,ensure_ascii=False,indent=2))
