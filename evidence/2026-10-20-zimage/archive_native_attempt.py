"""Preserve a known native-failed blue-teapot attempt before an isolated retry."""
import json
import shutil
from datetime import datetime,timezone
from pathlib import Path
import psutil

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
folder=HERE/'cases/zimage-gguf-prompt-change'
assert not (folder/'result.json').exists() and not (folder/'history.json').exists()
submission=json.loads((folder/'submission.json').read_text(encoding='utf-8'))
logroot=ROOT/'trials/2026-10-19-features'
stderr=logroot/'server-zimage-gpu-text.stderr.log'
text=stderr.read_text(encoding='utf-8',errors='replace')
assert 'Windows fatal exception: access violation' in text and 'partially_unload' in text
attempt=folder/'attempts/001-native-access-violation'
assert attempt.resolve().is_relative_to(folder.resolve())
attempt.mkdir(parents=True,exist_ok=False)
processes=[]
pid=int((logroot/'server-zimage-gpu-text.pid').read_text().strip())
try:
    parent=psutil.Process(pid)
    for proc in [parent]+parent.children(recursive=True):
        argv=proc.cmdline()
        if Path(proc.cwd()).resolve()==ROOT and any(a.replace('\\','/').endswith('ComfyUI/main.py') for a in argv):
            processes.append(proc)
except psutil.NoSuchProcess: pass
proof=[dict(pid=p.pid,created=p.create_time(),argv=p.cmdline()) for p in processes]
for proc in reversed(processes):
    try: proc.terminate()
    except psutil.NoSuchProcess: pass
psutil.wait_procs(processes,timeout=10)
for source in folder.iterdir():
    if source.is_file():
        target=attempt/source.name
        assert source.resolve().is_relative_to(folder.resolve()) and target.resolve().is_relative_to(attempt.resolve())
        source.rename(target)
shutil.copy2(stderr,attempt/'server.stderr.log')
shutil.copy2(logroot/'server-zimage-gpu-text.stdout.log',attempt/'server.stdout.log')
summary=dict(status='native_access_violation_no_output',prompt_id=submission['prompt_id'],
             phase='ComfyUI-GGUF GGMLTensor.to during model_patcher.partially_unload on second prompt',
             captured_at=datetime.now(timezone.utc).isoformat(),output_images=[],server_processes_stopped=proof,
             next_attempt='Known failed process stopped; retry same feature in an independent fresh service. No fabricated terminal API history.')
(attempt/'attempt-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
