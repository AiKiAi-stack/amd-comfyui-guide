"""Create independent, unsubmitted feature cases from the pinned API graphs."""
import json
import copy
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROBE = 'trials/2026-10-20-flux2-klein/gpu-probes/20261020T111553Z/result.json'
PHOTO = 'A photorealistic studio photograph of a glossy red ceramic teapot beside two ripe lemons on a dark wooden table, soft window light from the left, realistic ceramic reflections, sharp detail, no people, no letters, no watermark.'
ENGLISH = 'A straight-on product photograph of a single cafe sign. The sign has exactly one large word: "HELLO". Bold black sans-serif letters on a clean white rectangular sign, centered, plain blue wall behind it, no other text.'
CHINESE = '一张正面拍摄的咖啡馆招牌照片。白色长方形招牌上只写四个清晰的大黑字：“你好世界”。文字居中，背景是纯蓝色墙面，没有其他文字，没有水印。'
ART = 'A tasteful charcoal life drawing of a clearly adult woman aged 35, seated in a relaxed studio pose, nonsexual full-body nude figure study, classical art school anatomy study, no sexual activity, textured paper, no text.'

def base(variant):
    path = HERE/'workflows'/f'{variant}.api.json'
    graph = json.loads(path.read_text(encoding='utf-8'))
    sampler = next(k for k,n in graph.items() if n['class_type'] == 'KSampler')
    return dict(workflow_api=f'workflows/{variant}.api.json', sampler_node=sampler,
                prompt_node=graph[sampler]['inputs']['positive'][0],
                latent_node=graph[sampler]['inputs']['latent_image'][0],
                save_node=next(k for k,n in graph.items() if n['class_type']=='SaveImage'),
                width=512, height=512, steps=9, seed=665025001,
                model='Z-Image-Turbo-AIO FP8' if variant=='aio' else 'Z-Image-Turbo GGUF Q4_K_M / Qwen3-4B Q4_K_M',
                source_url='https://mp.weixin.qq.com/s/b-JAe4AbZCc5SDCcutRU_Q' if variant=='aio' else 'https://mp.weixin.qq.com/s/ads74_hTHki3Kft18je04Q',
                refs=[], inputs=[], claim_level='用户提供离线正文；自编验收提示词；公共可追溯工作流',
                runtime_profile='计划配置，尚未执行：RX6650XT扩散；CPU文本编码/CPU VAE；关闭动态VRAM、lowvram、预留2GB、同步卸载；先512²，无额外LoRA')

def main():
    cases=[]
    def add(variant, suffix, feature, prompt, expected, **changes):
        case=base(variant)
        case.update(id=f'zimage-{variant}-{suffix}', feature=feature, prompt=prompt, expected=expected, **changes)
        cases.append(case)
    add('aio','photo-9step','写实文生图／源工作流9步',PHOTO,'红色陶瓷茶壶、两个柠檬、木桌与左侧窗光；审查材质和结构。')
    add('aio','photo-8step','文章推荐8步生成',PHOTO,'与9步同seed和提示词，独立保存8步输出；记录实际含加载耗时，勿直接称稳态速度。',steps=8)
    add('aio','photo-4step','文章4步效果比较',PHOTO,'与8/9步同seed和提示词，比较4步结构与画质；文章7秒宣称尚未本机验证。',steps=4)
    add('aio','english','英文文字渲染',ENGLISH,'画面只出现清楚且拼写正确的HELLO，没有多余字。',steps=8,seed=665025002)
    add('aio','chinese','中文文字渲染',CHINESE,'招牌准确显示你好世界四字，没有乱码或多余字。',steps=8,seed=665025003)
    add('aio','figure-art','非色情成年人体艺术探索',ART,'非色情成年人物炭笔习作；仅是功能探索，不能证明UN训练或相对原版更少限制。',steps=8,seed=665025004,
        claim_level='文章泛提NSFW；本checkpoint无特殊UN训练证据；自编非色情艺术测试')
    add('gguf','photo','双GGUF文生图／低显存运行',PHOTO,'相同写实场景能实际生成；记录峰值显存/内存和耗时后才评价8GB可运行。')
    add('gguf','prompt-change','平铺工作流修改提示词',PHOTO.replace('red ceramic teapot','blue ceramic teapot'),'保持seed、采样和尺寸；提示词由红壶变蓝壶，PNG嵌入prompt一致且视觉颜色变化。')
    add('gguf','english','量化版英文文字渲染',ENGLISH,'独立检查HELLO拼写，不用AIO结果代替。',seed=665025002)
    add('gguf','chinese','量化版中文文字渲染',CHINESE,'独立检查你好世界四字，不用AIO结果代替。',seed=665025003)
    for c in cases:
        if c['id'].endswith('prompt-change'):
            c['comparison_case']='zimage-gguf-photo'
        if c['id'].startswith('zimage-gguf'):
            c['deviations']='扩散Q4_K_M为正文推荐；编码器选择Q4_K_M，截图为Q4_K_S；公开仓库示例展平，非作者未公开网盘JSON。'
        else:
            c['deviations']='源活动采样链保持；源1152×1736降至512²作为小显存首轮诊断；仅覆盖提示词/seed/尺寸和指定步数。'
        c['memory_profile']='legacy-lowvram' if c['id']=='zimage-gguf-photo' else 'legacy-normalvram'
        if c['memory_profile']=='legacy-normalvram':
            c['runtime_profile']='计划配置，尚未执行：RX6650XT；CPU VAE；关闭动态VRAM、normalvram、预留2GB、同步卸载；候选GPU文本编码，实际设备须核对服务日志；512²，无额外LoRA'
        if c['id'].startswith('zimage-aio-'):
            c['memory_profile']='dynamic-nvme'
            c['runtime_profile']='计划配置：RX6650XT；G盘NVMe文件映射、动态VRAM、fast-disk、禁用锁页内存；CPU VAE、同步卸载、预留2GB；512²，文本实际设备以服务日志为准。'
    gpu_control=copy.deepcopy(next(c for c in cases if c['id']=='zimage-gguf-photo'))
    gpu_control.update(id='zimage-gguf-photo-gpu-text',feature='文本编码GPU配置对照／写实文生图',memory_profile='legacy-normalvram',
                       comparison_case='zimage-gguf-photo',runtime_profile=next(c['runtime_profile'] for c in cases if c['memory_profile']=='legacy-normalvram'),
                       expected='与CPU文本编码基线同seed和提示词，独立出红壶与两个柠檬；核对实际CLIP设备，耗时含加载，不把差异视为严格速度倍率。')
    cases.append(gpu_control)
    next(c for c in cases if c['id']=='zimage-gguf-prompt-change')['comparison_case']=gpu_control['id']
    (HERE/'cases.json').write_text(json.dumps(cases,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    blocked=[dict(c, status='blocked_gpu_runtime', reason='尚未提交：最新独立GPU探针在mem_get_info原生崩溃，小矩阵未执行。需要恢复GPU后重检。', evidence=PROBE) for c in cases]
    (HERE/'blocked.json').write_text(json.dumps(blocked,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Prepared {len(cases)} case definitions; this script performs no submissions.')

if __name__=='__main__':
    main()
