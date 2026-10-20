# MOSS 8 步工作流核对

核对日期：2026-10-19。范围为本地 ComfyUI 代码、现有 API 图/日志，以及 OpenMOSS 与 Lodestones 的公开资料。没有运行 GPU、启动或停止进程、下载文件，亦未尝试获取被阻止的微信公众号原文。`Moss-Image-5B-Uncensored-8` 仅作为搜狗索引标题处理，不能据此确认文章所用模型或工作流。

## 结论

当前作者卡的 `Usage` 明确建议把 `lora.safetensors`（strength 1）或 `lora_latest.safetensors`（strength 0.7）直接交给 ComfyUI LoRA Loader；紧接着的旧 transformer/数据空间实现整节明确标为 `[Deprecated] ignore this section`。因此不能把旧节里的 `time_embedding.safetensors`、`dataspace.safetensors` / Q / step codes、FP32 限制当作当前 Comfy LoRA 用法的必需项。

当前卡正文仍称模型是 8 network evaluations、no CFG，并提到训练 caption 分布，但当前 Usage 没有给出 KSampler 的步数、sampler、scheduler、shift 等完整参数，也没有随仓库提供 8 步 Comfy workflow JSON。本机已验证 LoRA 的 safetensors 头只有常规 `diffusion_model.*.lora_down/up` / alpha 张量，metadata 为 rank 128、alpha 128；它没有包含 `dataspace` 或 timestep code。该结构与直接走 Comfy LoRA Loader 相符，但头部本身不编码采样方案。结论应限定为：**作者当前明确推荐直接加 LoRA；“标准 KSampler 8 步、CFG=1”是可测试候选，参数未获作者完整说明，不能先宣称已复现其结果。**

## 本机核心与 50 步基础图

本机 ComfyUI 代码（当前检出 `ce1e922d8623bb507180e32a0c01a7d0e29edef7`）已有 MOSS 模型检测、`supported_models.MOSSImage`、MOSS Qwen3.5 文本编码器和专用 LoRA key 映射。因此标准 SFT 文生图无需额外 MOSS loader 插件；`UNETLoader` + `CLIPLoader(type="moss_image")` + `VAELoader` 的模型路由正确。专用 MOSS tokenizer 会把普通文本自动包装成 Qwen chat 模板并打开 thinking block，提示词不必手写 ChatML，也不强制使用 JSON。

本机内置 `supported_models.MOSSImage.sampling_settings` 明确设为 `multiplier=1.0, shift=5.0`。`ModelSamplingDiscreteFlow` 原生读取模型设置；但 `ModelSamplingSD3.patch()` 的签名默认 `multiplier=1000`，并显式调用 `set_parameters(shift=shift, multiplier=multiplier)`，所以 API 图只传 `shift=5` 时会覆盖 MOSS 原生 multiplier。`ModelBase._apply_model()` 随后通过 `model_sampling.timestep(sigma)` 把 sigma 转成传给网络的 timestep；对 MOSS 的原生倍率 1 与 SD3 patch 的倍率 1000，模型收到的 timestep 相差 1000 倍。`ModelSamplingAuraFlow.patch_aura()` 固定传 `multiplier=1.0`。对于本机核心内置 MOSS（`UNETLoader`），应保留模型原生采样设置，或使用 `ModelSamplingAuraFlow` 并显式设 `shift=5`；不要直接套用 SD3 节点的默认 multiplier。

已有 `moss-api.json` 使用 512×512、Euler、`sgm_uniform`、50 步、CFG 3 和 `ModelSamplingSD3` shift 5。它曾返回成功并生成图像，但图像是满屏纹理噪声；由于该图的 SD3 patch 覆盖了 MOSS 原生时间尺度，这次 API 成功不算可用的 50 步基线，也不能据此判断模型或 INT8 fallback 的图像质量。修正节点后必须重新提交并检查新图。当前 `run_image_model.py` 已将 MOSS 图改用 `ModelSamplingAuraFlow` shift 5；待这张修正图成功解码且内容正常后，再记录有效耗时。512×512 是指南支持的下限（0.25MP；边长应为 16 的倍数），但指南推荐约 1–2MP；官方示例为 1024×1024。当前图包含官方推荐的负向分支跳过第 22 层节点（`single_layers="22"`、`double_layers=""`、start 0、end 1），并用 Euler / `sgm_uniform`、CFG 3、shift 5，接近 OpenMOSS 的标准采样设置。当前负向词在语法上可用；指南给出的推荐负向词是 `nsfw, worst quality, bad anatomy, watermark, jpeg artifact`。这些属于 50 步基线设置，不会把它变成 8 步 DMD。

作者称这版 DMD 是用紧凑 JSON `scene_graph` caption 训练，但同一模型卡的使用示例也传入普通英语句子。故基础图不缺强制 prompt 格式；8 步 LoRA 候选可先用普通英语以便和基础图同 seed 对照，再视结果比较训练风格 JSON。

官方插件的 50 步工作流用 `MOSSImageHFLoader` 加载 Diffusers 目录，并接 `ModelSamplingSD3` shift 5；该节点是在官方插件工作流上下文中的设置，不能不加区分地替换成核心内置 MOSS 的 `UNETLoader` 后照搬。核心模型的原生 `multiplier=1.0` 与 SD3 节点默认 `1000` 不同。当前历史中的成功任务虽然完成采样和解码，但输出为纹理噪声，因此有效的 50 步基线尚待用修正后的时间尺度重跑验证；本任务未探测或操作运行中进程。

## 官方工作流边界与下一步

- OpenMOSS 发布的 `moss-image.json` 是 **MOSS-Image-Base 的 50 步插件工作流**（CFG 3、shift 5、负向跳过第 22 层、Euler / `sgm_uniform`、1024²），经其 `MOSSImageHFLoader` 加载 Diffusers 格式的本地模型目录，并包含 `ModelSamplingSD3` 节点。这个节点配置不应直接移植到本机核心内置 MOSS `UNETLoader` 图；后者原生 multiplier 是 1.0，而本地 `ModelSamplingSD3` 未暴露 multiplier 输入、默认重置为 1000。核心图可不加采样 patch，或用 `ModelSamplingAuraFlow` shift 5。
- Comfy-Org 发布的 `image_moss_image_base_t2i_bboxes.json` 是 Base 布局工作流，使用常规 Comfy 采样；LoRA 仓库没有提供可拖入的 8 步 Comfy 工作流。
- 先用核心原生采样设置（或 `ModelSamplingAuraFlow` shift 5）重新得到可用的 50 步 SFT INT8 基线，并记录提交、history、图像与有效耗时；现有 INT8 fallback 的 50 步“成功”输出也是噪声图，不能计为可用结果。之后再用现有 LoRA 做一张同 seed 对照候选：`LoraLoaderModelOnly` strength 1，KSampler steps 8、CFG 1、Euler / `sgm_uniform`、denoise 1，保持相同 prompt/分辨率，并保留 MOSS 原生采样设置或使用 `ModelSamplingAuraFlow` shift 5。这里的 strength 1 来自作者当前 README；八次评估、no CFG 来自模型卡；Euler、`sgm_uniform`、shift 5 沿用官方 SFT 基线。由于 LoRA 卡未明确其 sampler/scheduler/shift，结果需标成“基于当前 Usage 的 Comfy 8 步候选试跑”，不能声称参数是作者已指定的完整配方。若作者后续公开设置或候选不理想，再按新资料复核；不要把已标 Deprecated 的旧算法直接当成必需步骤。

## 来源

- [Lodestones MOSS-Image-SFT-8-steps-dmd 当前模型卡](https://huggingface.co/lodestones/MOSS-Image-SFT-8-steps-dmd) 与 [本机下载 revision f95df83 的 README 更新](https://huggingface.co/lodestones/MOSS-Image-SFT-8-steps-dmd/commit/f95df83b5e90ae91ea412434b3f9b7f1c8c6314f)：当前 Usage 给出直接 ComfyUI 加载和 strength；老算法节标为 Deprecated。
- [OpenMOSS MOSS-Image ComfyUI 说明](https://github.com/OpenMOSS/MOSS-Image/blob/main/comfyui/README.md) 与 [官方示例工作流](https://github.com/OpenMOSS/MOSS-Image/blob/main/comfyui/moss-image/example_workflows/moss-image.json)：50 步 Base 示例和节点接法。
- [OpenMOSS 用户指南](https://github.com/OpenMOSS/MOSS-Image/blob/main/USERGUIDE.md) 与 [MOSS-Image-SFT 模型卡](https://huggingface.co/OpenMOSS-Team/MOSS-Image-SFT)：标准采样和提示建议。
- [Comfy-Org MOSS Base 工作流模板](https://github.com/Comfy-Org/workflow_templates/blob/main/templates/image_moss_image_base_t2i_bboxes.json)：Comfy 官方模板，非 Lodestones DMD 工作流。
