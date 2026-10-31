"""Refresh coverage only from recorded results plus manual image verdicts."""
import json
from datetime import datetime,timezone
from pathlib import Path

HERE=Path(__file__).resolve().parent
cases=json.loads((HERE/'cases.json').read_text(encoding='utf-8'))
reviews=json.loads((HERE/'reviews.json').read_text(encoding='utf-8'))
results={}
for case in cases:
    path=HERE/'cases'/case['id']/'result.json'
    if path.exists():
        result=json.loads(path.read_text(encoding='utf-8'))
        assert result['status']=='success' and result['output_validation_status']=='passed'
        assert reviews[case['id']]['verdict']=='通过'
        results[case['id']]=result
assert len(results)==10
path=HERE/'coverage.json'
coverage=json.loads(path.read_text(encoding='utf-8'))
coverage['updated_at']=datetime.now(timezone.utc).isoformat()
state=coverage['execution_status']
aio=[c['id'] for c in cases if c['id'].startswith('zimage-aio-')]
state.update(status='planned_feature_cases_reviewed',summary='Six AIO and four GGUF feature cases have real outputs with PNG/API bindings and manual visual passes. The CPU-text diagnostic baseline was operator-stopped without output. Optional branches and article resolution/speed claims remain unverified.',
             aio_status='six_outputs_visually_passed_same_service',aio_completed_output_case_ids=aio,aio_visual_review_pass_case_ids=aio,
             aio_visual_review_pending_case_ids=[],aio_submitted_pending_result_case_ids=[],aio_not_yet_submitted_case_ids=[])
for feature in coverage['mapped_features']:
    case_id=feature['case_id']
    if case_id not in results: continue
    result=results[case_id]
    image=Path(result['images'][0])
    feature.update(status='passed_visual_review',output='ComfyUI/output/FeatureBench/'+image.name,
        output_sha256=result['image_metadata'][0]['sha256'],result=f'cases/{case_id}/result.json',review='reviews.json#'+case_id,
        elapsed_seconds_after_submission=result['elapsed_seconds'],runtime_profile=result['runtime_profile'],observed=reviews[case_id]['detail'])
    if case_id.startswith('zimage-aio-'):
        feature['limit']='512-square tested in a single six-case serial service session. Optional LoRA/high-resolution branch, BF16 comparison, 1024 speed and 6GB operation remain unverified.'
        if case_id.endswith('figure-art'):
            feature['limit']+=' Nonsexual adult art does not establish special UN training or fewer restrictions relative to stock.'
    feature.pop('planned_profile',None)
for item in coverage['unverified_claims_or_optional_branches']:
    if item['claim'].startswith('1024-square'):
        item['reason']='All completed outputs are 512-square. AIO 4-step output completed in 20.08 seconds after submission in a warm service; it is not a test of the article resolution or 7-second claim.'
    if item['claim'].startswith('6GB compatibility'):
        item.update(claim='6GB compatibility',reason='Only an 8GB RX 6650 XT was used. Continuous execution was tested separately: six AIO cases passed in one service; the second GGUF prompt crashed during unload and required an independent-service retry.')
coverage['continuous_execution']=dict(aio='Six consecutive cases completed successfully in one service.',gguf='Same-service second prompt raised native access violation in GGUF partially_unload. Fresh-service retry passed. No continuous stability claim.')
path.write_text(json.dumps(coverage,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
lines=['# Z-Image：来源、权重与本地验证','',f"核对时间：{coverage['updated_at']}。六项 AIO 与四项 GGUF 功能测试已出图，并分别完成 PNG/API 绑定校验和人工目视复核。CPU 文本编码诊断基线被人工中止，无输出；不是画质失败。",'',
       '来源为用户提供的离线正文。来源作者、日期、原始 HTML 校验、固定模型版本与工作流边界分别见 [AIO 审计](source-aio.md)、[GGUF 审计](source-gguf.md)。未重新访问受阻微信原文，也未执行离线下载目录中的脚本。','',
       '## 功能与实际输出','']
for case in cases:
    if case['id'] not in results: continue
    result=results[case['id']]
    image=Path(result['images'][0])
    lines.append(f"- **{case['feature']}**：目视通过；提交后 {result['elapsed_seconds']} 秒。[图片](../../ComfyUI/output/FeatureBench/{image.name}) · [结果](cases/{case['id']}/result.json)。")
lines+=['','AIO 9/8/4步使用同一提示词与seed；8步与4步复用服务和缓存。三张均保留红茶壶、两个柠檬与左侧窗光，反射与表面细节随步数变化，不外推全部提示词质量。AIO与GGUF采样器不同，跨模型时长不构成量化精度的单变量比较。',
        '','## 启动、内存与稳定性','',
        'AIO 首项9步：提交后50.23秒，日志采样约19.8秒；服务冷启动242.66秒，含健康检查等完整编排309.95秒。计时见 [isolation-timing.json](cases/zimage-aio-photo-9step/isolation-timing.json)。G盘模型路径、动态VRAM及GPU文本编码由实际服务日志确认；CPU VAE。六项在同一服务连续成功，日志快照在 `service-logs/isolated-zimage-aio-photo-9step/`。',
        '',f"AIO 六项周期观测最大值：整机RAM {max(results[k]['observed_peak_host_ram_used_bytes'] for k in aio):,} 字节，显存 {max(results[k]['observed_peak_vram_used_bytes'] for k in aio):,} 字节。这是采样看到的最大值，非精确峰值，整机RAM包含系统和其他程序。",'',
        'GGUF 第二张同进程任务在 `GGMLTensor.to / partially_unload` 出现原生访问异常 `0xC0000005`，没有图片。[失败证据](cases/zimage-gguf-prompt-change/attempts/001-native-access-violation/attempt-summary.json) 完整保留。重新启动独立服务后蓝壶、英文和中文均成功，不能据此宣称GGUF连续运行稳定。红壶变蓝壶是修改提示词的文生图，不是输入图片编辑。',
        '', 'CPU文本编码基线因长时间加载、整机可用RAM低于0.5GB而停止：[operator-stop.json](cases/zimage-gguf-photo/operator-stop.json)。失败与中止证据不会用成功图片替换。',
        '', '## 存储与验证边界','',
        '实际磁盘布局为 D盘 SATA HDD、G盘 NVMe SSD。四份Z-Image权重均保留D盘原件，在G盘复制后重新核对SHA-256一致；见 [权重清单](download-manifest.json) 和 [覆盖记录](coverage.json)。G盘AIO实际加载路径已在日志确认。GGUF成功配置也改变了文本编码设备与存储条件，不能归因单一SSD速度倍率；程序与Python依赖仍在D盘，启动读取也受其影响。',
        '', '本轮只验证512×512、AIO FP8和双GGUF Q4_K_M。未比较Q3/Q4、BF16/FP8，未验证1024分辨率速度、6GB显卡、可选LoRA或1.5倍高分辨率分支。非色情成年人体艺术输出不证明特殊UN训练。',
        '', '完整图文报告：[feature-report.html](../../report/index.html)。逐项图、提示词、工作流、校验、耗时和目视判定见 [cases.json](cases.json)、[reviews.json](reviews.json) 与各case目录。','']
(HERE/'README.md').write_text('\n'.join(lines),encoding='utf-8')
print('Published ten visually checked feature outputs; optional claims remain unverified.')
