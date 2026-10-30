# Kroma / Krea 2 image-reference API workflow audit

核对时间：2026-10-19。范围：本地 `D:/AI/barely-comfy\ComfyUI` 官方核心节点、内置蓝图，以及官方 ComfyUI/Krea/Kroma 上游材料。没有启动模型、运行 GPU、改核心、下载模型或安装节点。

## 结论

本机 ComfyUI 核心存在 Krea2 的多参考图条件路径。最小本地 API 图是：`LoadImage` → `TextEncodeQwenImageEditPlus`（接 Krea2 CLIP 和 VAE、最多 3 张图）→ `FluxKontextMultiReferenceLatentMethod`（选 `index_timestep_zero`）→ KSampler positive。negative 依官方蓝图接同一 conditioning 的 `ConditioningZeroOut` 输出；采样 latent 仍用 `EmptyLatentImage`。

这条路径会把参考图送进 Qwen3-VL 视觉编码，并由 VAE 生成 `reference_latents`；Krea2 的 `model_base.py` 把它们传给 DiT，DiT 把它们拼进图像 token 序列。`index_timestep_zero` 设置参考 token 的特殊 timestep 处理。它与只把 VAEEncode 接到 KSampler latent、再调低 denoise 的普通 img2img 不同。

但“核心代码能够接收 references”不等于任意 Krea2 checkpoint 都学会了特定编辑语义。官方本地风格参考蓝图明确使用专门的 `krea2_turbo_int8_convrot.safetensors` 和 `krea2_style_reference.safetensors`；官方文档称该路线用于 1–2 张风格参考图。Kroma Q2 的已验证事实是既有 T2I 成功；Kroma 的上游卡将其列作 Krea2 架构的 T2I 微调/GGUF 量化，没有提供参考编辑训练说明。故可对 Kroma Q2 提交下面的图来验证实际效果，但目前不能把它标成已验证的 style reference 或身份编辑功能。也没有内置的专用“角色换头”节点或保证身份保持的核心能力。

## 本地 API 最小增量

在 `evidence/2026-10-18/kroma-api.json` 的节点 4 替换为下方 encoder，并添加图片输入节点 10/11、参考方法节点 12。把原 KSampler 节点 7 的 `positive` 改为 `['12', 0]`、`negative` 改为 `['5', 0]`。文件须先放入 ComfyUI input 目录（或经 `/upload/image` 上传，并在 `LoadImage.image` 使用服务器返回的文件名）。不接的 `image2`/`image3` 可省略；要多图时按顺序连接，最多三张。

```json
"10": {"class_type": "LoadImage", "inputs": {"image": "reference_a.png"}},
"11": {"class_type": "LoadImage", "inputs": {"image": "reference_b.png"}},
"4": {
  "class_type": "TextEncodeQwenImageEditPlus",
  "inputs": {
    "clip": ["2", 0],
    "vae": ["3", 0],
    "image1": ["10", 0],
    "image2": ["11", 0],
    "prompt": "Use picture 1 as the scene and pose reference. Use picture 2 as the identity reference. Replace only the adult subject's head while keeping the rest of picture 1 unchanged."
  }
},
"12": {
  "class_type": "FluxKontextMultiReferenceLatentMethod",
  "inputs": {
    "conditioning": ["4", 0],
    "reference_latents_method": "index_timestep_zero"
  }
},
"5": {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["12", 0]}}
```

若只测单图风格参考，保留 `image1`，prompt 让文字决定主体与构图、参考图决定视觉风格；但 Kroma 的风格效果必须作为实验结果验证。对于官方 Krea2 风格路径，模板用 `LoraLoaderModelOnly` 加专用 `krea2_style_reference.safetensors`，且使用不同的 INT8 ConvRot diffusion model；不要假设该 LoRA 可直接作用于 Kroma GGUF，当前没有本机兼容性验证。

角色换头实验可把原场景放在 `image1`、目标身份图放 `image2`，prompt 分别指明两图的用途。但普通风格参考 LoRA并非身份换头 LoRA；即使节点成功执行，也只能判作一次通用的多参考编辑实验，不能视作核心承诺的换头功能。需要较稳的局部替换，应另行评估带身份编辑训练的 LoRA、蒙版/inpaint 或专用编辑节点。

## 不要混淆的另一条路径：Krea 托管 API

`Krea2ImageNode` / `Krea2StyleReferenceNode` 是 `partner/image/Krea` 下的 API 节点：它把参考图上传到 Krea/Comfy API 存储，再向 Krea 云端生成端点发送 URL 和 strength。节点支持最多 10 张风格参考，但这不是本机加载的 Kroma Q2 在本地推理，也不应放进本地 `/prompt` 测试来声称 Kroma 本地参考能力。

## 本机实现证据

- `ComfyUI/comfy_extras/nodes_qwen.py:54-107`：`TextEncodeQwenImageEditPlus` 有 `image1`/`image2`/`image3`，将存在的图片放进 CLIP vision 输入；当接 VAE 时同时把每张图 encode 并写入 conditioning 的 `reference_latents`。
- `ComfyUI/comfy_extras/nodes_flux.py:154-179`：`FluxKontextMultiReferenceLatentMethod` 可设置 `index_timestep_zero`。
- `ComfyUI/comfy/model_base.py:2770-2796`：本机 `Krea2` 接收 `reference_latents`，转为 `ref_latents` 并传递 method。
- `ComfyUI/comfy/ldm/krea2/model.py:312-337`：DiT 只有在 ref method 不为 None 时才附加 ref token；`index_timestep_zero` 对 ref token 设特殊 timestep，并只解码目标图对应 token。
- `ComfyUI/blueprints/Image Style Reference (Krea-2 Turbo).json:1353-1496`：本机官方蓝图正好连接 Edit Plus encoder → `index_timestep_zero` → zero-out negative；蓝图还要求 `krea2_style_reference.safetensors`。
- 已成功的基础 Kroma T2I API 图：[kroma-api.json](../../../evidence/2026-10-18/kroma-api.json)。

## 上游主要来源

- [Comfy-Org Krea 2 Turbo INT8 Image Style Reference workflow](https://github.com/Comfy-Org/workflow_templates/blob/main/templates/image_krea2_turbo_int8_image_style_reference.json)：官方本地工作流、参考图输入、指定 diffusion model 与 style LoRA。
- [ComfyUI Krea 2 guide](https://github.com/Comfy-Org/docs/blob/main/tutorials/image/krea/krea-2.mdx)：官方文档说明 style-ref 工作流使用专门 model + LoRA，文档示例称 1–2 张参考图。
- [Comfy-Org Krea API style-reference workflow](https://github.com/Comfy-Org/workflow_templates/blob/main/templates/api_krea2_style_reference.json) 和 [Krea2StyleReferenceNode source](https://github.com/Comfy-Org/ComfyUI/blob/master/comfy_api_nodes/nodes_krea.py)：另行验证云端 API 路径，最多 10 张，图像会上传并以 URL 传送。
- [Kroma GGUF model card](https://huggingface.co/Abiray/Kroma-v0.3.1-Turbo-OPD-GGUF)：本机 Q2_K 文件所属模型仓库，标为 Krea2 架构 / T2I GGUF 量化。
- [Lodestones Kroma model page](https://huggingface.co/lodestones/Kroma)：Kroma 上游页面；可用于判断它是 Krea2 微调，不可据此推断它包含风格参考或身份编辑训练。
- [Krea 2 official inference repository](https://github.com/krea-ai/krea-2)：Krea 开源权重和推理入口说明。
