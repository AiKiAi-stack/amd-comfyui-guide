"""Update only unsubmitted AIO plans and the inspected Chinese image verdict."""
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
path=HERE/'cases.json'
cases=json.loads(path.read_text(encoding='utf-8'))
for case in cases:
    if case['id'].startswith('zimage-aio-'):
        assert not (HERE/'cases'/case['id']/'submission.json').exists()
        case['memory_profile']='dynamic-nvme'
        case['runtime_profile']='计划配置：RX6650XT；G盘NVMe文件映射、动态VRAM、fast-disk、禁用锁页内存；CPU VAE、同步卸载、预留2GB；512²，文本实际设备以服务日志为准。'
path.write_text(json.dumps(cases,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
path=HERE/'reviews.json'
reviews=json.loads(path.read_text(encoding='utf-8'))
reviews['zimage-gguf-chinese']=dict(verdict='通过',detail='目视确认白色招牌上恰好四个清晰黑字你好世界，分两行排列、背景蓝墙，无多余文字。512²，Q4_K_M双GGUF，独立服务；提交后75.34秒，不含服务启动。',image='zimage-gguf-chinese_00001_.png')
path.write_text(json.dumps(reviews,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Updated six unsubmitted AIO plans and the visually inspected Chinese verdict.')
