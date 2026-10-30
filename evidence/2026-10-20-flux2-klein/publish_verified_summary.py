"""Publish per-feature evidence, including partial and failed visual results."""
import hashlib
import json
import shutil
from datetime import datetime,timezone
from pathlib import Path
import requests

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def read(path): return json.loads(path.read_text(encoding='utf-8'))
def save(path,value): path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
cases=read(HERE/'cases.json')
reviews=read(HERE/'reviews.json')
ids=['flux2-klein-single-color-pinned','flux2-klein-dual-logo','flux2-klein-dual-people','flux2-klein-style','flux2-klein-replace-zh','flux2-klein-remove','flux2-klein-iterative']
case_by_id={c['id']:c for c in cases}
results={}
features=[]
for case in cases:
    folder=HERE/'cases'/case['id']
    result_path=folder/'result.json'
    if not result_path.exists(): continue
    result=read(result_path)
    results[case['id']]=result
    samples_path=folder/'resource-samples.jsonl'
    if samples_path.exists():
        samples=[json.loads(line) for line in samples_path.read_text(encoding='utf-8').splitlines() if line.strip()]
        max_ram=max(s['host_ram']['used_bytes'] for s in samples)
        min_available=min(s['host_ram']['available_bytes'] for s in samples)
        max_vram=max((d['vram_total']-d['vram_free'] for s in samples for d in s.get('api_devices',[]) if '6650' in d['name']),default=None)
        save(folder/'resource-summary.json',dict(samples=len(samples),observed_max_host_ram_used_bytes=max_ram,observed_min_host_ram_available_bytes=min_available,
            observed_max_vram_used_bytes=max_vram,note='Periodic observed maxima, not precise peaks. Host RAM includes the OS and other processes.'))
for case_id in ids:
    result=results[case_id]
    assert result['status']=='success' and result['binding_validation']['passed']
    assert case_id in reviews and Path(result['images'][0]).is_file()
    features.append(dict(case_id=case_id,feature=case_by_id[case_id]['feature'],visual_verdict=reviews[case_id]['verdict'],review=reviews[case_id]['notes'],
                         output_image=result['images'][0],image_metadata=result['image_metadata'],input_metadata=result['input_metadata'],
                         elapsed_seconds_after_submission=result['elapsed_seconds'],result=f'cases/{case_id}/result.json',resource_summary=f'cases/{case_id}/resource-summary.json'))
logs=HERE/'service-logs'
logs.mkdir(exist_ok=True)
log_records=[]
for label in ['flux2-klein-nvme','flux2-klein-nvme-pinned']:
    for kind in ['stderr','stdout']:
        source=ROOT/'trials/2026-10-19-features'/f'server-{label}.{kind}.log'
        target=logs/source.name
        shutil.copy2(source,target)
        log_records.append(dict(path=str(target),sha256=hashlib.sha256(target.read_bytes()).hexdigest()))
now=datetime.now(timezone.utc).isoformat()
stats=requests.get('http://127.0.0.1:8188/system_stats',timeout=5).json()
queue=requests.get('http://127.0.0.1:8188/queue',timeout=5).json()
assert not queue['queue_running'] and not queue['queue_pending']
last_probe=sorted((HERE/'gpu-probes').glob('*/result.json'))[-1]
save(HERE/'runtime-state.json',dict(updated_at=now,server_ready=True,queue_idle=True,actual_system_stats=stats,
    latest_small_gpu_probe=str(last_probe),historical_native_failure='gpu-runtime-block.json',profile='dynamic-nvme-pinned',
    note='API availability and recorded small GPU probe are separate evidence; successful diffusion outputs are listed in coverage.json. No driver reset or reboot was performed.'))
coverage=dict(updated_at=now,status='seven_planned_edit_features_tested_with_partial_results',features=features,
    partial_case_ids=[f['case_id'] for f in features if f['visual_verdict'].startswith('部分')],
    diagnostic_cases=[dict(case_id=i,result=f'cases/{i}/result.json',visual_review=reviews[i],images=results[i].get('images',[])) for i in ['flux2-klein-single-color','flux2-klein-t2i-nvme-control','flux2-klein-t2i-pinned-control']],
    runtime_findings='Two API-success outputs with disabled pinned memory were noise. Removing only that intended launch parameter in a new service restored T2I and all seven edits. This scopes a correctness issue to this local combination; low-level HIP/WDDM cause is not established.',
    scope='Editing references use about 0.25 MP and preserve aspect ratio; output is not necessarily 512-square. No new 1024 test; historical 1024 native abort without output remains preserved. Timings exclude ComfyUI cold startup.',logs=log_records)
save(HERE/'coverage.json',coverage)
for path in [HERE/'blocked.json',ROOT/'trials/2026-10-19-features/blocked.json']:
    blocked=read(path)
    save(path,[item for item in blocked if item.get('id') not in results])
pending_path=ROOT/'research/pending-models.json'
pending=read(pending_path)
for item in pending:
    if 'XNsQ6n0' in item['source_url']:
        item.update(status=coverage['status'],output_images=[f['output_image'] for f in features],feature_results=features,
            runtime_state='trials/2026-10-20-flux2-klein/runtime-state.json',runtime_block_history=item.pop('runtime_block',None),
            next_step='Seven planned edit features have real reviewed outputs. Inspect three partial results and preserve the two noise diagnostics; 1024 remains unverified after historical native failure.',latest_gpu_probe=str(last_probe))
    elif item.get('trial_folder')=='trials/2026-10-20-zimage':
        item.update(status='planned_features_tested_512_optional_claims_unverified',next_step='Ten Z-Image outputs reviewed. 1024/6GB/quantization comparisons and optional branches remain unverified.')
save(pending_path,pending)
lines=['# FLUX.2 Klein：七项编辑验收','',f'更新于 {now}。设备 RX6650XT 8GB、16GB RAM；七项均有独立输入、prompt/workflow、history、PNG绑定校验与人工目视结论。','',
    '## Feature → output','']
for f in features:
    lines.append(f"- **{f['feature']} — {f['visual_verdict']}**，提交后{f['elapsed_seconds_after_submission']}秒。[输出](../../ComfyUI/output/FeatureBench/{Path(f['output_image']).name}) · [结果]({f['result']})。{f['review']}")
lines+=['','## 噪声诊断与运行边界','',coverage['runtime_findings'],
    '', '两个噪声PNG与API成功记录均作为独立case保留；白包改蓝包成功重试没有覆盖失败图。迭代输入为已通过蓝包输出的同SHA副本，未使用失败图。',
    '', '本机有效配置：G盘NVMe镜像、--enable-dynamic-vram、--fast-disk、默认锁页内存、--reserve-vram 2.0、--fp8_e4m3fn-text-enc、--cpu-vae、--disable-async-offload。此处不要加入--disable-pinned-memory；同参数AIO能工作不能外推Flux也正常。',
    '',coverage['scope'],'', '三份权重保留D盘原件，G盘副本SHA校验一致；各 `.ssd-verified.json` 及 `download-manifest.json` 记录确切版本。没有下载新版本权重或替代模型。',
    '', '來源：[文章核对](../../research/new-articles-2026-10-20.md) · [固定工作流说明](workflows/recipe.md) · [逐项覆盖与资源记录](coverage.json)。工作流说明是准备阶段快照，实际执行/输入路径以case证据为准。',
    '', '总图文报告：[feature-report.html](../2026-10-19-features/feature-report.html)。','']
(HERE/'README.md').write_text('\n'.join(lines),encoding='utf-8')
print(json.dumps(dict(features=len(features),partial=len(coverage['partial_case_ids']),queue_idle=True),ensure_ascii=False))
