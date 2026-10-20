"""Preserve the noise verdict and prepare a single changed-runtime control."""
import copy
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
path=HERE/'reviews.json'
reviews=json.loads(path.read_text(encoding='utf-8'))
reviews['flux2-klein-t2i-nvme-control']=dict(verdict='失败／噪声图',notes='目视确认全幅重复噪声纹理，没有猫、咖啡馆或HELLO；API success和全图绑定通过不代表视觉成功。同服务T2I对照也失败，说明问题不局限于参考编辑链。提交后21.44秒，不含服务启动；与旧成功服务存在多项运行参数差异，尚不能归因单项。')
path.write_text(json.dumps(reviews,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
path=HERE/'cases.json'
cases=json.loads(path.read_text(encoding='utf-8'))
case=copy.deepcopy(next(c for c in cases if c['id']=='flux2-klein-t2i-nvme-control'))
case.update(id='flux2-klein-t2i-pinned-control',feature='诊断对照／恢复默认锁页内存',memory_profile='dynamic-nvme-pinned',
    comparison_case='flux2-klein-t2i-nvme-control',runtime_profile='计划单变量参数对照：同NVMe/动态VRAM/reserve2/FP8文本配置，只去掉--disable-pinned-memory；必须新服务，存在缓存及启动差异，不作为严格速度对照。')
assert not any(c['id']==case['id'] for c in cases)
cases.append(case)
path.write_text(json.dumps(cases,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
