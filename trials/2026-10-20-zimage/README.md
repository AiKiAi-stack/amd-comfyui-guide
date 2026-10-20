# Z-Image：来源、权重与本地验证

核对时间：2026-10-20T14:09:23.261822+00:00。六项 AIO 与四项 GGUF 功能测试已出图，并分别完成 PNG/API 绑定校验和人工目视复核。CPU 文本编码诊断基线被人工中止，无输出；不是画质失败。

来源为用户提供的离线正文。来源作者、日期、原始 HTML 校验、固定模型版本与工作流边界分别见 [AIO 审计](source-aio.md)、[GGUF 审计](source-gguf.md)。未重新访问受阻微信原文，也未执行离线下载目录中的脚本。

## 功能与实际输出

- **写实文生图／源工作流9步**：目视通过；提交后 50.23 秒。[图片](../../ComfyUI/output/FeatureBench/zimage-aio-photo-9step_00001_.png) · [结果](cases/zimage-aio-photo-9step/result.json)。
- **文章推荐8步生成**：目视通过；提交后 30.09 秒。[图片](../../ComfyUI/output/FeatureBench/zimage-aio-photo-8step_00001_.png) · [结果](cases/zimage-aio-photo-8step/result.json)。
- **文章4步效果比较**：目视通过；提交后 20.08 秒。[图片](../../ComfyUI/output/FeatureBench/zimage-aio-photo-4step_00001_.png) · [结果](cases/zimage-aio-photo-4step/result.json)。
- **英文文字渲染**：目视通过；提交后 30.97 秒。[图片](../../ComfyUI/output/FeatureBench/zimage-aio-english_00001_.png) · [结果](cases/zimage-aio-english/result.json)。
- **中文文字渲染**：目视通过；提交后 30.17 秒。[图片](../../ComfyUI/output/FeatureBench/zimage-aio-chinese_00001_.png) · [结果](cases/zimage-aio-chinese/result.json)。
- **非色情成年人体艺术探索**：目视通过；提交后 30.16 秒。[图片](../../ComfyUI/output/FeatureBench/zimage-aio-figure-art_00001_.png) · [结果](cases/zimage-aio-figure-art/result.json)。
- **平铺工作流修改提示词**：目视通过；提交后 125.77 秒。[图片](../../ComfyUI/output/FeatureBench/zimage-gguf-prompt-change_00001_.png) · [结果](cases/zimage-gguf-prompt-change/result.json)。
- **量化版英文文字渲染**：目视通过；提交后 85.47 秒。[图片](../../ComfyUI/output/FeatureBench/zimage-gguf-english_00001_.png) · [结果](cases/zimage-gguf-english/result.json)。
- **量化版中文文字渲染**：目视通过；提交后 75.34 秒。[图片](../../ComfyUI/output/FeatureBench/zimage-gguf-chinese_00001_.png) · [结果](cases/zimage-gguf-chinese/result.json)。
- **文本编码GPU配置对照／写实文生图**：目视通过；提交后 124.59 秒。[图片](../../ComfyUI/output/FeatureBench/zimage-gguf-photo-gpu-text_00001_.png) · [结果](cases/zimage-gguf-photo-gpu-text/result.json)。

AIO 9/8/4步使用同一提示词与seed；8步与4步复用服务和缓存。三张均保留红茶壶、两个柠檬与左侧窗光，反射与表面细节随步数变化，不外推全部提示词质量。AIO与GGUF采样器不同，跨模型时长不构成量化精度的单变量比较。

## 启动、内存与稳定性

AIO 首项9步：提交后50.23秒，日志采样约19.8秒；服务冷启动242.66秒，含健康检查等完整编排309.95秒。计时见 [isolation-timing.json](cases/zimage-aio-photo-9step/isolation-timing.json)。G盘模型路径、动态VRAM及GPU文本编码由实际服务日志确认；CPU VAE。六项在同一服务连续成功，日志快照在 `service-logs/isolated-zimage-aio-photo-9step/`。

AIO 六项周期观测最大值：整机RAM 9,484,845,056 字节，显存 5,105,554,944 字节。这是采样看到的最大值，非精确峰值，整机RAM包含系统和其他程序。

GGUF 第二张同进程任务在 `GGMLTensor.to / partially_unload` 出现原生访问异常 `0xC0000005`，没有图片。[失败证据](cases/zimage-gguf-prompt-change/attempts/001-native-access-violation/attempt-summary.json) 完整保留。重新启动独立服务后蓝壶、英文和中文均成功，不能据此宣称GGUF连续运行稳定。红壶变蓝壶是修改提示词的文生图，不是输入图片编辑。

CPU文本编码基线因长时间加载、整机可用RAM低于0.5GB而停止：[operator-stop.json](cases/zimage-gguf-photo/operator-stop.json)。失败与中止证据不会用成功图片替换。

## 存储与验证边界

实际磁盘布局为 D盘 SATA HDD、G盘 NVMe SSD。四份Z-Image权重均保留D盘原件，在G盘复制后重新核对SHA-256一致；见 [权重清单](download-manifest.json) 和 [覆盖记录](coverage.json)。G盘AIO实际加载路径已在日志确认。GGUF成功配置也改变了文本编码设备与存储条件，不能归因单一SSD速度倍率；程序与Python依赖仍在D盘，启动读取也受其影响。

本轮只验证512×512、AIO FP8和双GGUF Q4_K_M。未比较Q3/Q4、BF16/FP8，未验证1024分辨率速度、6GB显卡、可选LoRA或1.5倍高分辨率分支。非色情成年人体艺术输出不证明特殊UN训练。

完整图文报告：[feature-report.html](../2026-10-19-features/feature-report.html)。逐项图、提示词、工作流、校验、耗时和目视判定见 [cases.json](cases.json)、[reviews.json](reviews.json) 与各case目录。
