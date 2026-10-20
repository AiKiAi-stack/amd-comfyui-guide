"""Refresh trial state from real probes, submissions, results and reviews."""
import json
from datetime import datetime, timezone
from pathlib import Path
import requests

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def read(path, default=None):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default
def save(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

cases=read(HERE/'cases.json')
probe_path=sorted((ROOT/'trials/2026-10-20-flux2-klein/gpu-probes').glob('*/result.json'))[-1]
probe=read(probe_path)
results={c['id']:read(HERE/'cases'/c['id']/'result.json') for c in cases}
results={k:v for k,v in results.items() if v}
submitted=sum((HERE/'cases'/c['id']/'submission.json').exists() for c in cases)
stopped=sum((HERE/'cases'/c['id']/'operator-stop.json').exists() for c in cases)
active=sum((HERE/'cases'/c['id']/'submission.json').exists() and c['id'] not in results and not (HERE/'cases'/c['id']/'operator-stop.json').exists() for c in cases)
images=[p for r in results.values() for p in r.get('images',[]) if Path(p).is_file()]
status=read(HERE/'preparation-status.json',{})
try:
    response=requests.get('http://127.0.0.1:8188/system_stats',timeout=3)
    response.raise_for_status()
    server=response.json()
except requests.RequestException:
    server=None
reviews=read(HERE/'reviews.json',{})
reviewed=sum(reviews.get(k,{}).get('verdict')=='通过' for k in results)
concluded=len(results)+stopped
state=('planned_cases_concluded_with_operator_stop' if concluded==len(cases) and reviewed==len(results) and stopped
       else 'all_cases_executed_pending_visual_review' if len(results)==len(cases)
       else 'partially_tested' if results else 'gpu_ready_running_trials' if active and probe['healthy']
       else 'gpu_ready_server_ready' if server and probe['healthy'] else 'gpu_ready_preparing_server' if probe['healthy']
       else 'weights_verified_gpu_runtime_blocked')
status.update(updated_at=datetime.now(timezone.utc).isoformat(),status=state,cases_prepared=len(cases),
              cases_submitted=submitted,cases_with_results=len(results),output_images=images,
              cases_operator_stopped=stopped,cases_awaiting_terminal_result=active,
              cases_visually_passed=reviewed,cases_concluded=concluded,
              latest_gpu_probe=str(probe_path),gpu_healthy=probe['healthy'],server_ready=server is not None,
              blocker=None if probe['healthy'] else 'Latest GPU probe did not pass; inspect its stage and logs.',
              next_step=('Ten Z-Image feature outputs reviewed; CPU baseline stopped without output. Resume remaining FLUX editing cases. Optional branches and 1024-speed claims remain unverified.' if concluded==len(cases) and reviewed==len(results)
                         else 'Continue independent local cases and visually review actual outputs.') if probe['healthy'] else 'Resolve GPU probe failure before inference.')
save(HERE/'preparation-status.json',status)
pending_path=ROOT/'research/pending-models.json'
pending=read(pending_path)
for item in pending:
    own=[c for c in cases if c['source_url']==item['source_url']]
    if own:
        own_results=[results[c['id']] for c in own if c['id'] in results]
        item.update(status='partially_tested' if own_results else state,output_images=[p for r in own_results for p in r.get('images',[])],
                    next_step=status['next_step'],latest_gpu_probe=str(probe_path))
    elif 'XNsQ6n0' in item['source_url'] and probe['healthy']:
        item.update(status='partially_tested_ready_to_resume',next_step='Resume seven remaining edit cases after the current Z-Image batch.',latest_gpu_probe=str(probe_path))
save(pending_path,pending)
for path in [HERE/'blocked.json',ROOT/'trials/2026-10-19-features/blocked.json',ROOT/'trials/2026-10-20-flux2-klein/blocked.json']:
    blocked=read(path,[])
    for item in blocked:
        if item['id'].startswith('zimage-') and (HERE/'cases'/item['id']/'operator-stop.json').exists():
            item.update(status='operator_stopped_no_output',reason='CPU文本配置耗时过长且整机可用内存低于0.5GB；API中止后装载仍未返回，已结束本任务服务。无输出，不判为模型功能失败。',evidence=str((HERE/'cases'/item['id']/'operator-stop.json').relative_to(ROOT)))
        elif item['id'].startswith('zimage-') and (HERE/'cases'/item['id']/'submission.json').exists():
            item.update(status='submitted_waiting_result',reason='本案例已提交；实际终态和输出仍待核对。',evidence=str((HERE/'cases'/item['id']/'submission.json').relative_to(ROOT)))
        elif probe['healthy'] and (item['id'].startswith('zimage-') or item['id'].startswith('flux2-klein-')):
            item.update(status='queued_for_local_trial',reason='重启后GPU小测试已通过；本案例尚未提交，等待顺序实测。',evidence=str(probe_path.relative_to(ROOT)))
    save(path,blocked)
print(json.dumps({k:status[k] for k in ['status','cases_submitted','cases_with_results','gpu_healthy','server_ready']},ensure_ascii=False))
