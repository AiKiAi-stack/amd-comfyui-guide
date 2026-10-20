"""Change only unsubmitted editing plans; retain executed T2I records."""
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
path=HERE/'cases.json'
cases=json.loads(path.read_text(encoding='utf-8'))
changed=[]
for case in cases:
    if case['recipe']=='t2i': continue
    assert not (HERE/'cases'/case['id']/'submission.json').exists()
    case['memory_profile']='dynamic-nvme'
    case['runtime_profile']='计划配置：G盘NVMe模型镜像、动态VRAM/fast-disk、禁用锁页内存、CPU VAE/同步卸载、预留2GB；FP8文本编码GPU计算；4步Euler/Flux2Scheduler/CFG1；约0.25MP编辑。实际参数由API预检与服务日志确认。'
    changed.append(case['id'])
path.write_text(json.dumps(cases,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Prepared unsubmitted NVMe edit plans:',changed)
