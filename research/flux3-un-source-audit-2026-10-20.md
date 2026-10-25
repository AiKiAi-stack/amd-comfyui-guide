# Flux.3-5.6B-UN 来源与本机可执行性审计

审计日期：2026-10-20。范围：公开作者镜像、公开站外演示摘要、FLUX 3 Image Klein 官方上游资料，以及本机 ComfyUI 代码和已存在的模型文件。此轮只读；没有访问微信正文、下载模型、启动 GPU 或运行推理。

## 结论

`Flux.3-5.6B-UN` 的作者镜像确实公开声称 4 步、8G、文生图、图像编辑、图生图、自动提示词和批量任务，但没有列权重文件名、量化格式或节点图。现有证据不能确定“UN”代表什么，也不能确定它改的是图像主干权重、文本编码器，还是两者都改了。标准 FLUX 3 Image Klein 的官方资料是一个可供设计候选工作流的参照，不能据此认定它就是作者整合包，也不能把其功能或 8GB NVIDIA 结果归给 UN。

本机已具备 ComfyUI 原生 FLUX3 节点、Qwen3-VL-4B FP8 编码器候选和 Flux2 VAE 候选，但 `models/diffusion_models` 中没有 FLUX3 主干权重。因此本机目前没有可运行的 FLUX3/UN 输出；已存在的编码器和 VAE 只能作为未来候选复用，兼容性尚未实测。

## 来源分级与已知信息

### A 级：作者认证的 Compshare 镜像页面

[作者镜像](https://www.compshare.cn/images/uc0UnUzrIbtD) 标题为 `Flux.3-5.6B-UN`，描述声称 4 步迭代、8G 显存可用、文生图、图像编辑、图生图（洗图）、自动提示词和批量任务。页面标注 v1.0、2026-10-18 更新、镜像大小 150GB、CUDA 13.2、支持卡型包括 A800 与 RTX50 系等，并提示初始化后通过 SD-WEBUI 按钮操作。页面显示作者认证。

这些是**镜像页面的功能与部署声明**，不是独立显存基准或本机兼容性证明。150GB 是镜像大小，不是主模型权重文件的大小。页面没有公布 checkpoint 文件清单、权重来源/哈希、量化、ComfyUI 节点图或 8G 卡型的完整型号。页面有文生图、图像编辑、图生图的截图链接；本轮图片资源抓取未成功，未从截图推断模型选择项。

### B 级：作者公开视频的站外摘要

[BBS 站外页面](https://bbs.monster/thread-5320-1-1.html) 将其内容标为刘悦视频摘要，称原视频发表于 2026-10-18 22:26:39（北京时间）。摘要描述演示了 4 步文生图、单图修改、双图修改，并称视频结尾给出自定义 ComfyUI 端口 8187；没有提供完整节点搭建或全部参数。自动提示词和批量任务虽出现在标题中，但摘要明确表示短视频未逐项解释配置。

这是第三方对公开视频的文字整理，不是作者镜像文件清单，也不是微信原文。链接到 B 站的视频页本轮返回 HTTP 412，未读取视频本体。

### C 级：用户提供的 Quark 分享页，本轮浏览器已复核

本轮通过浏览器直接读取[用户提供的分享页](https://example.invalid/private-share-removed)，确认 `Flux.3-Image-5.6B-UN.part1.rar` 至 `part4.rar`，页面合计36.2G：前三卷各9.8G、末卷6.9G，修改日期均为2026-10-18。页面显示登录账号入口与扫码/手机号登录弹窗；当前没有已登录下载会话。尚未下载、解包或检查内部文件，也未绕过登录。分卷名称不能揭示内部 transformer、encoder、LoRA、量化或依赖，文件日期也不能当作微信文章日期。

### 微信文章

用户提供的微信正文仍未读取。本报告没有使用代理、镜像、缓存或其他方式获取该正文；因此不把镜像更新日期当作文章发布日期，也不称已核对微信文章标题。

## 与官方 FLUX 3 Image Klein 的区别

[Black Forest Labs 官方发布说明](https://bfl.ai/blog/flux-3-image-klein) 将 FLUX 3 Image Klein 描述为 5.6B 图像生成器，列出文生图、图像编辑和最多 10 张参考图；发布了 base 和蒸馏版本，并提到 FP8、INT8、NVFP4 构建。BFL 明确说 5.6B 参数计数指图像生成器，文本编码器另计。官方 INT8 的“8GB”说明限定在 NVIDIA GeForce RTX；NVFP4 需要 Blackwell。它不证明 AMD RX 6650 XT 兼容，也不证明作者的 UN 使用了该官方模型。

[官方 base 模型卡](https://huggingface.co/black-forest-labs/flux-3-image-klein-base) 指定 Qwen3-VL-4B-Instruct 为独立文本编码器，base 为未蒸馏模型，参考设置 50 步、CFG 3.5；蒸馏模型用于生成/编辑，卡片列 16 步、无 guidance。官方 ComfyUI 包列有以下**标准 Klein**文件：

- `diffusion_models/flux3-image-klein-int8-convrot.safetensors`，5.8 GB，蒸馏主干；另有 BF16 11.1 GB、NVFP4 5.3 GB 变体。
- `text_encoders/qwen3vl_4b_int8_convrot.safetensors`，4.9 GB；另有 BF16 8.9 GB。
- `vae/flux2-vae.safetensors`，0.3 GB。
- 可选自动提示词模型 `qwen3.5_9b_flux3_prompt_upsampler_w4a8.safetensors`，6.7 GB；官方包也有更大的 BF16/INT8 版本。

[官方 ComfyUI 蒸馏图像编辑模板](https://github.com/Comfy-Org/workflow_templates/blob/main/templates/image_flux3_klein_distilled_image_edit.json) 使用 INT8 蒸馏主干、Qwen3-VL-4B INT8、Flux2 VAE；其 KSampler 为 16 步、CFG 1、Euler / Simple。它的多图参考逻辑把参考图依序映射到 `<ref_image_0>`、`<ref_image_1>` 等，并将参考图接入正负条件。该模板的自动提示词部分是单独的 Qwen 3.5 模型和节点，不应当作主干内建能力。标准 Klein 的 4 步演示和上述 16 步官方模板属于不同来源/配置；不以其中一个推断 UN 的步数或效果。

因此当前能够说的是：**标准 Klein 官方架构**是 5.6B 图像主干 + 独立 Qwen3-VL-4B 文本编码器 + Flux2 VAE。作者 `Flux.3-5.6B-UN` 的组件组成仍未知。标题中的 “UN” 不足以判断它是否表示取消审查、替换文本编码器或替换主干。

## 本机 ComfyUI 与已有文件

本机代码确认原生支持标准 FLUX3 加载，无需为基础节点先假设必须安装自定义节点：

- [ComfyUI/nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/ce1e922d8623bb507180e32a0c01a7d0e29edef7/nodes.py) 的 `CLIPLoader` 类型列表包含 `flux3`，并允许 `device=cpu`。
- [ComfyUI/comfy/sd.py](https://github.com/Comfy-Org/ComfyUI/blob/ce1e922d8623bb507180e32a0c01a7d0e29edef7/comfy/sd.py) 有 `FLUX3` 的 Qwen3-VL-4B 文本编码器分支；[model_base.py](https://github.com/Comfy-Org/ComfyUI/blob/ce1e922d8623bb507180e32a0c01a7d0e29edef7/comfy/model_base.py) 和 [model_detection.py](https://github.com/Comfy-Org/ComfyUI/blob/ce1e922d8623bb507180e32a0c01a7d0e29edef7/comfy/model_detection.py) 含 FLUX3 主干识别/模型类。
- `ComfyUI/models/diffusion_models` 当前没有 FLUX3 主干文件；现有文件为 Kroma、MOSS 与 Qwen Image 模型。
- 已有 `ComfyUI/models/text_encoders/qwen3vl_4b_fp8_scaled.safetensors`，5,242,467,968 bytes。下载记录标明它来自 [Comfy-Org/Krea-2](../trials/2026-10-18/kroma-download.json)，是 Qwen3-VL-4B FP8 变体，不是官方 FLUX3 包中的 INT8 ConvRot 文件。原生加载代码能够按 Qwen3-VL-4B 结构选择 FLUX3 文本分支，使其成为**合理的复用候选**；但编码器权重来源/训练版本与 BFL 精确文件不同，加载成功和条件效果都未在 FLUX3 上验证。
- 已有 `ComfyUI/models/vae/flux2-vae_small.safetensors`，249,521,340 bytes，来自 [Comfy-Org/MOSS-Image](../trials/2026-10-18/moss-download.json)。它与 BFL Comfy 包的 `flux2-vae.safetensors` 名称/来源不同，结构是否完全一致、能否直接解码 FLUX3 latent 未比较；仅列为 VAE 候选，不能称已确认兼容。

本机已有的编码器和 VAE 不提供扩散主干；仅有它们无法运行 FLUX3。这里没有加载文件、启动服务或进行 GPU/CPU 推理。

## 面向本机的最小候选方案（不是 UN 配方，也未实测）

如后续要先验证**标准 FLUX3 Klein 蒸馏版**，低下载量候选是取得官方 INT8 蒸馏主干（5.8 GB），试用本机现有 Qwen3-VL-4B FP8 与 Flux2 VAE 候选：`UNETLoader` + `CLIPLoader(type="flux3", device="cpu")` + `VAELoader`，再接 `CLIPTextEncode`、`EmptyFlux2LatentImage`、`KSampler`、`VAEDecode`。建议首轮 512×512、batch 1，按官方蒸馏模板从 16 步 / CFG 1 / Euler / Simple 起测，并手写充分的场景描述，不加载可选 9B 自动提示词模型。该方案复用了本地文件，磁盘新增候选约 5.8 GB；使用现有文件前仍需验证各节点加载与 VAE 输出。

这只是给 RX 6650 XT 8GB / 16GB RAM 准备的**资源受限诊断起点**：官方 8GB 声明针对 NVIDIA RTX，不能外推到 AMD；INT8 ConvRot 在本机 ROCm/gfx1032 的支持情况、FP8 encoder 的显存/内存路径、VAE 对应性和实际峰值都未知。CPU 编码器会占用系统内存，16GB 机器是否有足够余量也尚未测量。512 分辨率和 CPU encoder 是降低首轮峰值的尝试，不是成功保证。若目标是作者的 UN 包，必须先得到其精确权重、量化和工作流；不能把上述官方 Klein 候选当作 UN 替代品，也不能把作者 4 步设置直接套到官方蒸馏检查点。

## 可复核来源

- 作者镜像：[Compshare — Flux.3-5.6B-UN](https://www.compshare.cn/images/uc0UnUzrIbtD)
- 站外演示摘要：[Monster BBS — Flux.3 5.6B整合包入门](https://bbs.monster/thread-5320-1-1.html)；原视频 [Bilibili BV1iYnV6SEbt](https://www.bilibili.com/video/BV1iYnV6SEbt/) 本轮未能打开。
- 上游说明：[BFL FLUX 3 Image Klein 发布说明](https://bfl.ai/blog/flux-3-image-klein)、[官方 base 模型卡](https://huggingface.co/black-forest-labs/flux-3-image-klein-base)、[Comfy 组件包](https://huggingface.co/black-forest-labs/flux-3-image-klein-comfy)、[Comfy 蒸馏编辑模板](https://github.com/Comfy-Org/workflow_templates/blob/main/templates/image_flux3_klein_distilled_image_edit.json)。

