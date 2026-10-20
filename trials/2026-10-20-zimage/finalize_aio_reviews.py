"""Save manual verdicts after inspecting each of the six actual AIO outputs."""
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
path=HERE/'reviews.json'
reviews=json.loads(path.read_text(encoding='utf-8'))
details={
    'photo-8step':'目视确认红釉茶壶、恰好两个柠檬、木桌和左窗光；与9步同seed及提示词，构图相近，未见明显结构退化。8步输出独立保存；复用已启动服务和缓存，不是冷启动速度。',
    'photo-4step':'目视确认红釉茶壶、恰好两个柠檬、木桌和左窗光；与8/9步同seed及提示词。主体与布局保留，壶身反射细节、柠檬表皮细节略有变化；本例未见明显结构缺损，不外推全部提示词质量。复用已启动服务和缓存。',
    'english':'目视确认白色招牌上只有HELLO，字母完整且拼写正确，蓝色背景墙，没有多余文字。',
    'chinese':'目视确认白色招牌上准确显示你好世界四字，分两行排列，背景为蓝墙，没有乱码或多余文字。',
    'figure-art':'目视确认成年女性坐姿全身素描，纸张与炭笔质感、非色情艺术学习场景符合提示词。手脚细部只是生成结果，不宣称解剖精确；不构成特殊UN训练或比原版更少限制的证据。',
}
label='isolated-zimage-aio-photo-9step'
snapshot=HERE/'service-logs'/label
snapshot.mkdir(parents=True,exist_ok=True)
logfiles=[]
for kind in ['stderr','stdout']:
    source=ROOT/'trials/2026-10-19-features'/f'server-{label}.{kind}.log'
    target=snapshot/f'server.{kind}.log'
    shutil.copy2(source,target)
    logfiles.append(dict(path=str(target),sha256=hashlib.sha256(target.read_bytes()).hexdigest()))
for suffix,detail in details.items():
    case_id='zimage-aio-'+suffix
    folder=HERE/'cases'/case_id
    result=json.loads((folder/'result.json').read_text(encoding='utf-8'))
    assert result['status']=='success' and len(result['images'])==1
    assert Path(result['images'][0]).is_file()
    reviews[case_id]=dict(verdict='通过',detail=detail+f" 512²，AIO FP8/dynamic-nvme/GPU文本编码/CPU VAE；提交后{result['elapsed_seconds']}秒，未包含服务冷启动。",image=Path(result['images'][0]).name)
    (folder/'service-log-evidence.json').write_text(json.dumps(dict(captured_at=datetime.now(timezone.utc).isoformat(),service_label=label,shared_service=True,
        note='Six cases ran serially in this one service. Log snapshot includes all six cases; not an isolated per-case startup.',logs=logfiles),ensure_ascii=False,indent=2),encoding='utf-8')
path.write_text(json.dumps(reviews,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Saved five new manual verdicts and the full shared-service log snapshot. Six AIO visual reviews now recorded.')
