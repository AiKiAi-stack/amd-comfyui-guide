"""Keep the failed edit verdict and add a T2I control for the same live profile."""
import copy
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
path=HERE/'reviews.json'
reviews=json.loads(path.read_text(encoding='utf-8'))
reviews['flux2-klein-single-color']=dict(verdict='失败／噪声图',notes='API终态success、PNG/history/API绑定一致，但目视检查全幅重复噪声纹理，没有可辨手提包，白包改蓝包目标失败。提交后51.18秒；保留原图、参考输入SHA与dynamic-nvme运行证据。后续迭代不能用此图作为已通过的输入。')
path.write_text(json.dumps(reviews,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
path=HERE/'cases.json'
cases=json.loads(path.read_text(encoding='utf-8'))
case_id='flux2-klein-t2i-nvme-control'
assert not any(c['id']==case_id for c in cases)
case=copy.deepcopy(next(c for c in cases if c['id']=='flux2-klein-t2i-gpu-text'))
case.update(id=case_id,memory_profile='dynamic-nvme',feature='NVMe动态配置诊断／文生图对照',
    runtime_profile='计划诊断：与当前噪声编辑相同服务和dynamic-nvme配置；使用此前已通过的512²文生图提示词、seed和图，区分参考工作流与通用运行问题。',
    comparison_case='flux2-klein-t2i-gpu-text',claim_level='失败后的本地运行配置诊断，不是文章新增功能')
cases.append(case)
path.write_text(json.dumps(cases,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Recorded failed visual verdict; prepared one unsubmitted T2I runtime control.')
