"""Publish verified download readiness and genuinely unexecuted case status."""
import json
from datetime import datetime, timezone
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]

def read(path):
    return json.loads(path.read_text(encoding='utf-8'))

def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

manifest=read(HERE/'download-manifest.json')
verified=[]
for item in manifest:
    target=Path(item['target'])
    receipt=read(HERE/(target.name+'.verified.json'))
    assert target.stat().st_size==item['bytes'], target
    assert receipt['verified_sha256']==item['sha256'], target
    assert all(receipt[k]==item[k] for k in item), target
    verified.append(receipt)

cases=read(HERE/'cases.json')
assert len({c['id'] for c in cases})==len(cases)
assert not list((HERE/'cases').glob('*/submission.json')), 'Reconcile actual submissions first'
assert not list((HERE/'cases').glob('*/result.json')), 'Sync actual results instead of publishing unexecuted status'
probes=ROOT/'trials/2026-10-20-flux2-klein/gpu-probes'
latest=sorted(probes.glob('*/result.json'))[-1]
probe=read(latest)
assert probe['healthy'] is False, 'GPU state changed: reassess instead of publishing old blocker'
status=dict(updated_at=datetime.now(timezone.utc).isoformat(), status='weights_verified_gpu_runtime_blocked',
            weights=verified, total_weight_bytes=sum(i['bytes'] for i in manifest),
            workflow_api_files=['workflows/aio.api.json','workflows/gguf.api.json'],
            cases_prepared=len(cases), cases_submitted=0, output_images=[],
            latest_gpu_probe=str(latest), gpu_healthy=False,
            blocker='Fresh isolated torch process aborts in GPU memory query before tiny matmul; no new generation attempted.',
            next_step='User restarts Windows when convenient. Recheck GPU, start conservative server, validate server args and run one case at a time.')
save(HERE/'preparation-status.json',status)

pending_path=ROOT/'research/pending-models.json'
pending=read(pending_path)
for item in pending:
    if item['source_url'] not in {c['source_url'] for c in cases}:
        continue
    item.update(status=status['status'], output_images=[],
                download_manifest='trials/2026-10-20-zimage/download-manifest.json',
                preparation_status='trials/2026-10-20-zimage/preparation-status.json',
                next_step=status['next_step'])
    item['source_audit']='trials/2026-10-20-zimage/source-aio.md' if 'b-JAe4' in item['source_url'] else 'trials/2026-10-20-zimage/source-gguf.md'
save(pending_path,pending)

blocked_path=ROOT/'trials/2026-10-19-features/blocked.json'
blocked=read(blocked_path)
new=read(HERE/'blocked.json')
new_ids={c['id'] for c in new}
for c in new:
    c['evidence']=str(latest.relative_to(ROOT))
blocked=[c for c in blocked if c['id'] not in new_ids]+new
save(blocked_path,blocked)
save(HERE/'blocked.json',new)
audit=ROOT/'research/new-articles-2026-10-20.md'
text=audit.read_text(encoding='utf-8')
marker='## Z-Image 下载与未执行状态'
if marker not in text:
    text+='\n'+marker+'\n\n'
    text+='四项权重共 18,159,309,094 bytes，均通过完整文件 SHA-256 校验。已准备 AIO 6 案例、双 GGUF 4 案例；两者均未提交推理，新增输出为零。\n\n'
    text+='本轮新 GPU 探针仍在 `torch.cuda.mem_get_info` 原生中止，16×16 matmul 未到达；最新探针路径记录于 `trials/2026-10-20-zimage/preparation-status.json`。运行器验证会在不健康探针处拒绝提交。没有自动重启或重置驱动。\n\n'
    text+='AIO 保留历史工作流 res_multistep/simple/shift3/CFG1，比较9/8/4步；GGUF保持公开示例Euler/simple/shift3/CFG1/9步。第一轮均降至512²，不能当1024²能力验证。GGUF编码器选择Q4_K_M，与文章截图Q4_K_S不同，已明确记录；没有取得作者私盘JSON。\n'
    audit.write_text(text,encoding='utf-8')
print(json.dumps({k:v for k,v in status.items() if k!='weights'},ensure_ascii=False,indent=2))
