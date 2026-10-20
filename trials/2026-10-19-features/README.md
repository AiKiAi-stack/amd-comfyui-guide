# 功能与输出图逐项试验

用户目标：公众号介绍的模型除了普通编辑之外，各项功能都提供独立的输入、真实输出与判断。报告入口为 [feature-report.html](./feature-report.html) 和 [feature-report.md](./feature-report.md)。运行中的卡片不能当成最终结果。

2026-10-20 核验：BFS 换头 LoRA 对照和 Turbo-UN 六项均有真实输出；UN 的文生图、多图合成、全身角色替换及主要姿态目标达到本例目标，换头和遮罩物种替换仍有限制。H3 最新一轮换用 GPU FP16 VAE 并预留 2GB 显存后，保存了五张 PNG 和原始 WebP，含服务启动共433.08秒；这只是384×256、5帧、4步的链路诊断，不等于正常视频或BFS功能通过。此前CPU VAE超时、INT8 HIPBLAS错误、FP16无显存预留时的OOM均保留。自动提示词生成先后遇到INT8错误与fallback显存不足，没有输出。

## 试验边界

- RX 6650 XT 8GB、16GB RAM、Windows，现有 ROCm 7.14 / PyTorch 2.12 环境；本轮输出 512×512。旧基线尺寸见其原记录。
- 没有读取微信公众号原文。声明依据见 [来源核对](../../research/feature-claims-2026-10-19.md)，标题截断字不补写。
- 采用本机已下载且校验的权重组合，未取得作者整合包，不能声称完整复现作者工作流。
- `success` 是 ComfyUI 工作流返回状态，功能是否达到目标另记在 `reviews.json`。失败结果保留，不用其他模型的图补位。
- 多图参考、遮罩重绘、latent 图生图、风格参考分别记录，不把它们混为同一项。
- MOSS 使用默认关闭的 gfx1032 INT8 fallback；本进程开启后使用 ComfyUI 已有浮点反量化路径，避开该卡上缺失的原生 INT8 kernel。8步另加载 DMD LoRA，采样使用 AuraFlow shift 5（multiplier 1）。
- Kroma 参考试验沿用核心 Krea2 条件链，明确设置 `index_timestep_zero`；当前基础组合没有官方 style-reference LoRA 或 BFS 换头 LoRA。失败只说明所测组合没有达到目标。
- Kroma 原始参考节点内部升到 1024，实测反复 softmax OOM 后进程 Aborted，没有输出。保留到 `attempts/kroma-ref1024-*` 后改用独立 `VAEEncode + ReferenceLatent` 编码 512 参考，视觉编码仍为 384；三个参考任务随后实际出图。原始失败记录可由报告展开区查看。
- 对共用同一套模型的独立图，`BenchmarkConditioningBarrier` 仅原样传递条件，并让组内编码先完成，再采样；不混合各项提示词或条件值。它用于避开第二次请求 CLIP 时卸载 GGUF 的已观察崩溃。批次总耗时不能当成每张图的独立耗时。
- Qwen 局部重绘的遮罩外区域由工作流合成保留；不能把遮罩外像素一致全部归因于模型自身的编辑能力。
- Qwen 首个参考批次在缓存 K/V 的 `GGMLTensor.to` 路径发生原生访问冲突；独立进程的多图任务也复现。通过核心 `QwenImage21Cache(device=off)` 关闭 prefix 缓存后，多图任务实际成功出图（325.4 秒）。这项规避仅针对本机已观察的路径，不代表完整修复 GGUF/ROCm。原始失败均在 `attempts/` 留存。
- 局部重绘第一张图片是在崩溃批次中保存的。恢复工具逐项核对 PNG 内的节点类别/输入与原提交图后登记为 `partial_output`，不补写全批成功状态；其 mask/input 附件与像素统计另存。
- Turbo-UN 本轮使用 `--disable-dynamic-vram --lowvram` 将文字/视觉编码器留在 CPU，扩散在 GPU、VAE 在 CPU，且关闭 prefix 缓存；每项是否真正完成见 result/history。不能称纯 GPU 或已验证去限制效果。
- 角色替换、姿态参考探索复用普通双图指令编辑链路。`pose-guide.png` 是代码绘制的输入结构示意，不是模型生成结果；未使用专用姿态控制网络，也未复现作者整合界面。
- MiniMax H3 的隔离 Ref2VA 短片段加载诊断已通过。角色替换、视频续写、长音频等功能仍无对应输出，不能用五帧诊断图补位。实际成功图使用未量化 FP16 VAE，未启用INT8 fallback；API与命令见该卡片。

## 重跑步骤

1. 查看 `cases.json` 的功能、输入顺序、提示词与预期。每项的 `cases/<id>/api.json` 是实际提交的完整图。
2. 确认 8188 没有正在执行的任务，按模型启动独立服务：`.venv\Scripts\python.exe trials\2026-10-19-features\manage_server.py restart --model moss`（也支持 `kroma`、`qwen`、`turbo-un`）。脚本只停止此工作区记录在 PID 文件中的 ComfyUI 进程，活动队列会拒绝重启。
3. 等待 `READY`，执行 `.venv\Scripts\python.exe -u trials\2026-10-19-features\feature_bench.py moss`。支持 `--case <id>` 单项执行；已有 result.json 会跳过，保留原证据。更改设置时应使用新 case ID。
4. 核对 `submission.json`、`history.json`、`result.json` 与真实输出图片，视觉判断记入 `reviews.json`。API 成功不自动写成视觉通过。
5. 生成报告：`.venv\Scripts\python.exe trials\2026-10-19-features\build_report.py`。HTML 直接离线打开；可查看完整输入、输出和提示词。

已用的参考批次命令：

```powershell
.venv\Scripts\python.exe trials\2026-10-19-features\run_conditioning_batch.py kroma --cases kroma-style-ref,kroma-multiref,kroma-head-swap
.venv\Scripts\python.exe trials\2026-10-19-features\run_conditioning_batch.py qwen --cases qwen-inpaint,qwen-multiref,qwen-face-swap,qwen-style-edit,qwen-face-only
```

每项 `single-api.json` 保存独立图；`api.json` 保存实际提交的完整批次图，`output_nodes` 把该功能映射到专属保存节点。PNG 内的 node class / inputs 与提交图，以及每张图的 SHA-256 记录在 `output-audit.json`；ComfyUI 自动附加的 LoadImage 缓存哈希单独保留。

新增 Qwen BFS LoRA 的下载校验和配方边界见 [BFS 下载记录](../2026-10-19-bfs-headswap/download-receipt.json)。新增模型已确认为用户提供的 Flux.3-5.6B-UN，来源与待核验的内部权重见 [待测清单](../../research/pending-models.md)；尚无本机输出。

输出原件在 `ComfyUI/output/FeatureBench/`；引用素材在 `ComfyUI/input/featurebench/`。旧文生图基线在 `../2026-10-18/`，报告以单独的历史记录标明。

需要原生崩溃后的独立重试时，`run_isolated.py qwen --retry-errors --case <id>` 会先核对并归档旧 case 文件夹，再启动新进程；Turbo-UN 应使用 `run_isolated.py turbo-un --cpu-text`。不要同时运行两个 GPU 队列。`verify_outputs.py` 会检查真实文件、PNG 提交图绑定、SHA-256 和遮罩测量；图片质量仍需目测。

H3 成功诊断的重跑：先确保8188/8189没有其他GPU任务，在一个终端运行 `h3-sandbox\start-h3.ps1 -GpuVae -ReserveVram 2.0`，服务就绪后在另一终端运行 `h3-sandbox\submit-diagnostic.ps1 -NativeVae`。逐帧PNG和WebP保存在 `../2026-10-19-h3/output/h3/`。完整原始命令、工作流和history已随诊断卡保存，先前失败在原H3目录及 `attempts/` 中保留。
