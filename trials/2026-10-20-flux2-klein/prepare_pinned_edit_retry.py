"""Keep failed images intact and prepare a distinct pinned-memory edit retry."""
import copy
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
path=HERE/'reviews.json'
reviews=json.loads(path.read_text(encoding='utf-8'))
reviews['flux2-klein-t2i-pinned-control']=dict(verdict='通过',notes='目视确认清晰橘猫、咖啡馆雨夜霓虹、准确的HELLO招牌。与噪声T2I对照使用同一权重、G路径、seed、提示词及dynamic/reserve2/FP8配置，唯一有意改变的启动参数是去掉--disable-pinned-memory，使用新服务。恢复正常支持该参数在当前栈中影响正确性；并不识别底层HIP/拷贝根因，也不是严格速度倍率。提交后40.64秒，未含启动。背景仍有其他招牌文字，未严格满足no other writing。')
path.write_text(json.dumps(reviews,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
path=HERE/'cases.json'
cases=json.loads(path.read_text(encoding='utf-8'))
retry=copy.deepcopy(next(c for c in cases if c['id']=='flux2-klein-single-color'))
retry.update(id='flux2-klein-single-color-pinned',feature='单图编辑／改色（恢复锁页内存重试）',
    memory_profile='dynamic-nvme-pinned',retry_of='flux2-klein-single-color',creates_iterative_input=True)
assert not any(c['id']==retry['id'] for c in cases)
cases.append(retry)
for case in cases:
    if case['recipe']=='t2i' or case['id']=='flux2-klein-single-color': continue
    assert not (HERE/'cases'/case['id']/'submission.json').exists()
    case['memory_profile']='dynamic-nvme-pinned'
    case['runtime_profile']='计划配置：G盘NVMe、动态VRAM/fast-disk、默认锁页内存、CPU VAE/同步卸载、预留2GB；FP8文本GPU计算；4步Euler/Flux2Scheduler/CFG1，约0.25MP编辑。实际argv和图像绑定另有记录。'
    if case['id']=='flux2-klein-iterative':
        case['depends_on']=retry['id']
        case['refs']=['flux2-klein-bench/'+retry['id']+'.png']
        case['inputs']=list(case['refs'])
path.write_text(json.dumps(cases,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Prepared distinct retry plus six unsubmitted pinned-profile edits; failed records retained.')
