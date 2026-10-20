# Z-Image-Turbo-AIO 来源核对与 API 配方

核对范围是用户提供的离线文章快照和 Hugging Face 上游公开文件元数据、历史模型卡及工作流。本来源审计子任务没有请求微信原文、运行离线目录中的脚本、下载模型权重或启动 ComfyUI。主任务的权重下载与完整性检查单独记录于 `download-manifest.json` 和各文件的 `.verified.json`；GPU 执行状态见 `preparation-status.json`。

## 来源与版本身份

离线文章为《Z-Image 老少皆宜新知识，AIO模型和工作流！》，公众号“托尼不是塔克”，发布时间 `2025-12-11T23:59:00+08:00`。本机快照位于 `[private-article-snapshot]`；`metadata.json` 记录的原始 HTML SHA-256 是 `9946edf0d6aab4455debea11a3a38245a3b6084968527b7e4d4d57d5c5318179`，主任务已对 `01-original.html` 重新计算并核对。截图里的仓库文件清单、文件名和工作流名称与上游 2025-12-07 的 revision 对得上。

确切仓库是 [SeeSee21/Z-Image-Turbo-AIO](https://huggingface.co/SeeSee21/Z-Image-Turbo-AIO/tree/3614ae1a6ceec70d8b1b02f41df3af72ac756241)，固定 revision 为 `3614ae1a6ceec70d8b1b02f41df3af72ac756241`，上游 API 记录的更新时间是 `2025-12-07T18:06:32Z`。该 revision 的模型卡标为 Apache-2.0、基于 `Tongyi-MAI/Z-Image-Turbo`，并将其描述为集成 VAE 与文本编码器的 6B 参数 photorealistic 生成模型。

该版本 FP8 主文件为 `z-image-turbo-fp8-aio.safetensors`：**10,345,190,658 bytes（10.345 GB，约 9.635 GiB）**，SHA-256 `f569c42b6797a89e65e80c743d6dfd230ed9318237aa242c92777deb22fad660`。固定 revision 的 [FP8 文件页](https://huggingface.co/SeeSee21/Z-Image-Turbo-AIO/blob/3614ae1a6ceec70d8b1b02f41df3af72ac756241/z-image-turbo-fp8-aio.safetensors) 和 [精确下载地址](https://huggingface.co/SeeSee21/Z-Image-Turbo-AIO/resolve/3614ae1a6ceec70d8b1b02f41df3af72ac756241/z-image-turbo-fp8-aio.safetensors) 指向同一个文件；本次仅读取元数据，未下载权重。BF16 对照文件在该 revision 中为 20,522,566,986 bytes。

文章使用的工作流名 `z-image-turbo-aio-workflow.json` 在相同 revision 中大小为 27,561 bytes，Git blob `2c6f90b59f18834f50aba482879e975efac998d4`。它后来在 `0699365150ff6942abcd98264a05e0b11bb8bbb1` 提交中删除，父提交正是上述 `3614ae1...`；因此应使用固定历史链接，不能用当前 main 上重命名后的工作流假装是文章附件。[固定版本工作流 JSON](https://huggingface.co/SeeSee21/Z-Image-Turbo-AIO/blob/3614ae1a6ceec70d8b1b02f41df3af72ac756241/z-image-turbo-aio-workflow.json) 的本地副本 SHA-256 为 `1ef90efdc7c84a93e7c036dcd2a346027514511b7fa88857f1df329722f68053`。

## 工作流实际连接和采样参数

已读取并结构化核对固定版本工作流 JSON。工作流里共有 22 个节点；主分支是普通文生图：

`CheckpointLoaderSimple (34)` → `ModelSamplingAuraFlow (2, shift=3)` → `KSampler (17)` → `VAEDecode (11)` → `SaveImage (26)`。

提示支路由 `CheckpointLoaderSimple` 的 CLIP 输出进入 `CLIPTextEncode (20)`；正向 conditioning 直接进入采样器，负向支路经 `ConditioningZeroOut (40)`，所以不需要负面提示词。空 latent 由 `EmptyLatentImage (6)` 提供。检查点的 VAE 输出经两个 `Reroute` 到活动的 `VAEDecode (11)`，没有另载 VAE 或文本编码器。

源工作流中**实际启用**的主采样器是 9 steps、CFG 1、`res_multistep`、`simple`、denoise 1，固定 seed `322571269041708`；初始 latent 为 1152×1736、batch 1。工作流说明中另外列出 512×512 等快速尺寸，但保存的 latent 节点实际是 1152×1736。模型卡文字、工作流 Markdown 说明和文章都强调 8 steps，但该固定 JSON 的活动 `KSampler (17)` 字段是 **9**。因此保存的 API 基线照源节点保留 9 steps；若要复现文章文字，case 配置只将 `17.inputs.steps` 覆盖为 8。文章提到的 4 steps 是速度比较，不是该上游工作流默认值或已核实的推荐最优值；它也只应覆盖 steps，保持 CFG、采样器、scheduler、denoise、shift 原样。

LoRA 节点 `LoraLoader (41)` 在源文件中 mode=4（bypass），文件名为 `z-image\\woman877-zimage.safetensors`，不属于仓库主权重，也未在主分支生效。可选高分支包含 `LatentUpscaleBy` 1.5×、第二个 KSampler（8 steps、CFG 1、`res_multistep` / `simple`、denoise 0.55）和另一 SaveImage；这些节点在固定工作流中同样被 bypass。`Fast Groups Bypasser (rgthree)` 与 `Image Comparer (rgthree)` 是工作流 UI 组件，API prompt 不需要保留。文章提到的缺失节点提示因此对应 UI 导入工作流时的 `rgthree-comfy`，不构成基础 API 文生图的模型依赖。

可复核的小型源文件和转换结果：

- [固定 revision 的 HF API 元数据 JSON](source_workflows/api-model-revision-3614ae1a6ceec70d8b1b02f41df3af72ac756241.json)
- [固定 revision 的工作流原件](source_workflows/z-image-turbo-aio-workflow.json)
- [离线转换脚本](prepare_workflows.py)
- [ComfyUI API prompt（源工作流活动 9-step 分支）](workflows/aio.api.json)
- [API 节点绑定和 8/4-step case 覆盖说明](workflows/bindings-aio.json)

`prepare_workflows.py` 只读取上述两个本地小型源文件，核对 revision、工作流 SHA、模型文件大小和模型 SHA，再把活动分支转换为 ComfyUI API prompt。它解析实际 link，并只穿过源中已 bypass 的 LoRA 和 reroute；不会访问网络、改 cases、触碰权重或调用 ComfyUI。输出保留原始 1152×1736 latent；做低显存试跑时可由 case 选择尺寸，尺寸来自源图节点 6。

## 功能声明与限制

| 声明 | 来源与证据级别 | 审计结论 |
|---|---|---|
| 单文件 AIO，内含 VAE 与文本编码器 | 固定版 [上游模型卡](https://huggingface.co/SeeSee21/Z-Image-Turbo-AIO/blob/3614ae1a6ceec70d8b1b02f41df3af72ac756241/README.md) 与工作流实际 CheckpointLoader 接法；作者声明/结构佐证 | 可按一个 checkpoint 文生图配方测试；不是独立验证了权重内部张量。 |
| 逼真文生图、英文/中文文字渲染、8-step 快速生成 | 固定版上游模型卡；作者功能说明 | 主工作流只覆盖文生图。文字渲染和逼真度是上游宣称，本次未生成或视觉验收。 |
| 图像编辑、局部重绘、参考图控制 | 文章及固定旧工作流没有此类输入支路 | 该 AIO 基础工作流不支持据此声称这些功能。当前仓库另有 ControlNet 工作流和额外依赖，不能并入这份 2025 年简单 AIO 工作流结论。 |
| 文章泛称 AIO 通常含 NSFW 增强 | 离线文章的泛化描述 | 不是该 FP8 检查点经 NSFW 特训的证据。固定版模型卡没有对此文件作此声明。核对时当前 main revision 是 `0958c582880173e0cd09004baf00387ca92667d9`（HF API `lastModified=2026-01-03T14:49:06Z`）；该卡里的 “Partially NSFW capable” 说的是后来加入的**另一份 Anime 模型**（独立 `z-image-anime-aio-fp8.safetensors`），不能转写成 photorealistic FP8 的训练属性。[当前模型卡](https://huggingface.co/SeeSee21/Z-Image-Turbo-AIO/blob/0958c582880173e0cd09004baf00387ca92667d9/README.md) |
| 8 GB 显存能运行 | 固定版上游模型卡自述其 FP8 在 RTX 4060 8GB 上测试，分辨率 1920×1088、8 steps；属于作者报告的测试，不是本机测试 | 文件本身约 9.635 GiB，超过 8 GiB 显存约 1.635 GiB，因此不能把它理解为权重必然全驻显存。显存卸载/分块策略未在该说明里明确。本次未做 AMD RX 6650 XT 验证。 |

## 可测试配方边界

当前可建立一个单文件检查点的文生图试跑，优先保持源图主分支与其实际连线；AIO 本身不需要额外 VAE/CLIP 文件。源工作流有 9-step 活动基线；文章 8-step 和 4-step 对照由 `bindings-aio.json` 中的 `step_case_overrides` 描述，父 runner 可分别改 `KSampler (17).inputs.steps`。不要据此宣称 4 steps 已由上游工作流设置或本机验证。LoRA 默认不加载；高分辨率旁路也默认不启用。
