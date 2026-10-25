# 模型功能工作流库

按 `模型 / 功能 / 平台__案例.json` 整理；`ui/` 内为 ComfyUI 自己导出、重新载入后逐节点核对参数和连线的 WebUI 格式。`api/` 是对应 API 配方，不要将两种格式混淆。完整索引和校验状态见 [catalog.json](catalog.json)。

本机已安装到 WebUI 左侧 **工作流 → 模型功能库 → 模型 → 功能**。刷新工作流列表后打开，也可从汇报下载单个 UI JSON，使用“打开工作流”或拖入画布。输入图片已补齐到当前运行环境。

在另一套 ComfyUI 使用时，将 `ui/` 中所需 JSON 载入，将 `input/ModelLibrary_*` 复制到该环境 `ComfyUI/input/` 根目录；模型仍须自行准备。输入采用内容 hash 加原文件名的统一名称，便于前端选择；图片原件与像素不变。不同内容的现有文件不会被覆盖。原路径、原计算图、SHA256、转换说明均在索引中。

先用 Linux 已执行的四份预设：Qwen Base 的 blue / green 和 Z-Image 双 GGUF 的 zimage-1 / zimage-2。它们是已验收输出配方，不表示所有提示词均精确达到。Qwen 在仓库根使用 `bash scripts/start_ubuntu_qwen.sh`；Z-Image 历史 Linux 验证使用 `bash scripts/start_ubuntu.sh`。不要混淆两套配置，切换前确认队列为空并停止原服务。

Windows 历史工作流保留原权重、提示词、seed、采样器和输入顺序；提供 Linux 当前前端可载入的配方，**没有因此成为 Linux 执行通过**。部分历史结果来自分阶段/分进程方式，整图在当前 Linux 的执行与内存表现尚未验证。LoRA、换头、身份保持、CPU 反推、视频等原待办与部分达到结论保留。每份图中的使用说明列出来源和边界。

seed 的生成后控制设为 fixed。MOSS 布局采用 JSON 提示词，UI 中花括号使用转义，避免前端动态提示词解析破坏结构；实际提交的文本与历史 API 逐字一致。历史批量案例只抽取本案例输出和上游依赖，去掉仅负责等待的 BenchmarkConditioningBarrier，保持 conditioning 本身不变。

其他视频功能仍未验证。Flux.3-5.6B-UN 精确权重/配方没有确认，未虚构工作流，也未用 FLUX.2 的图代替。无法独立提取的记录在索引保留原因。

重新生成（在仓库根）：

```bash
python3 scripts/build_workflow_library.py
NODE_PATH=/home/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules /home/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node scripts/convert_workflow_library.cjs
python3 scripts/install_workflow_library.py
python3 scripts/build_platform_report.py
```

第一步读取本机 8188 的节点定义；第二步使用 Playwright 和本机 Chrome 做真实前端导入/导出，不排队执行模型；第三步安装至独立的“模型功能库”目录并生成包含输入的 zip。发现用户自行修改的同名工作流会停止以保留修改。README 中的 Node 路径是当前机器工具路径，不属于 ComfyUI Python 环境依赖。

模型执行与功能目视评价请查看 [模型 / 功能 / 平台汇报](../trials/2026-10-19-features/feature-report.html)，Windows 原报告归档保持原字节。


## 2026-10-25 Linux 补图后的使用方法（追加）

新增 Linux 实测按模型和功能归档。汇报中的“Linux 有输出图片”只统计真实采样输出，输入、遮罩预览不计入；图片正常与功能达到分别判断。Windows 原结论、原图、提示词和历史失败记录保留。

对于标注“分阶段”的新 Linux 案例，优先打开末尾为 **采样.json** 的文件：通常是 `02-采样`，辅助反推案例是 `03-采样`。本机已放好对应归档，保留原输入可直接采样。修改提示词、参考图或输入顺序时，从该案例第1阶段重新运行，阶段之间按说明重启服务并复制输出归档路径/SHA256。普通案例是“编码 → 采样”；4B辅助反推案例是“反推 → 编码 → 采样”。后者阶段2的 LoadRepairText 读取阶段1的原始描述，阶段3的 LoadRepairConditioning 读取阶段2条件，不需人工改写描述。只载入整图 JSON 不等同于完成这些步骤，标注“整图未验收”的文件不默认安装。

每份工作流画布的使用说明和汇报中的“复现步骤”均列出本例所需配置。切换模型前确认队列为空，按本例参数重启服务；不要同时运行验证服务和常用 WebUI。Qwen、Kroma、MOSS 可能需要 FP16/upcast，FLUX 和 Z-Image 使用各自实测配置；不能把一种启动配置的输出当作另一种配置的验证。UN GGUF 编码器和同目录的 mmproj 必须配套。

[完整包](https://github.com/AiKiAi-stack/barely-comfy/releases/download/linux-model-workflows-2026-10-25/model-feature-workflows.zip) 包含 UI、API、输入图片以及经过 SHA256 校验的反推文字/编码条件归档，不包含模型权重。解压后将 input 内容复制到目标 ComfyUI/input。编码归档只适用于配套的提示词和输入，不是模型文件。

[轻量包](https://github.com/AiKiAi-stack/barely-comfy/releases/download/linux-model-workflows-2026-10-25/model-feature-workflows-light.zip) 不含编码归档；在另一台机器上需要先运行相应的编码阶段，不能直接运行指向旧归档的采样阶段。两个包中的“UI 导入通过”只表示前端导入/导出一致，实际模型与功能状态以汇报为准。

不以其他模型图片补齐这些空缺。新 Linux 的换头/身份、LoRA、细节文字等部分达到项也保留实际评价，不因已有 PNG 而改成通过。


Qwen 中名称带 `cpu-encode` 的 Linux 案例，编码阶段使用 CPU/BF16。画布中“完整启动命令”可直接复制；其中的分块文本计算环境变量也要保留。采样阶段按对应说明去掉 `--cpu` 并重启，以使用 GPU。不要把 CPU 编码阶段的启动方式套用到其他模型；它们的实际配置在各自案例中列出。

2026-10-25 更新：当前268份API与268份WebUI格式工作流，184份推荐图安装到本机；分阶段的整图配方仍不视为执行验收。完整包包含本轮已验证的条件/文本归档，不包含模型权重。新输入须先重新编码并更新采样图的归档路径和SHA；跨进程启动配置见每份使用说明和汇报复现步骤。
