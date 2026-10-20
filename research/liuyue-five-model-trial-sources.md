# 刘悦公众号五项试机：MOSS、Kroma、MiniMax H3 来源核验

核验日期：2026-10-19（北京时间）。范围仅是搜狗微信索引中三项标题所对应的公开项目来源；未读取微信公众号原文，因此不能证明作者文内实际使用了以下权重、插件或工作流。权重体积和 SHA-256 取自 Hugging Face 模型所有者/Comfy-Org 的[仓库 API](https://huggingface.co/docs/hub/api#repo-api)。`GB` 以下均按十进制计算。未下载模型，未安装插件，也未在本机实测这三组模型。

## 1. MOSS-Image-5B-Uncensored-8 步

- [OpenMOSS 官方仓库](https://github.com/OpenMOSS/MOSS-Image)发布的是 Base 和 SFT，不存在一个经确认名为 `MOSS-Image-5B-Uncensored-8step` 的官方单文件模型。官方[ComfyUI 插件说明](https://github.com/OpenMOSS/MOSS-Image/blob/main/comfyui/README.md)使用完整 Diffusers 目录，含 transformer、text_encoder、tokenizer、vae；[官方用户指南](https://github.com/OpenMOSS/MOSS-Image/blob/main/USERGUIDE.md)对 Base 建议约 50 步。标题中“Uncensored”可能是作者对模型能力的描述，不能据此认定独立权重。第一步应核对其文章原文的实际链接。
- Comfy-Org 的[ComfyUI 单文件重打包](https://huggingface.co/Comfy-Org/MOSS-Image)为可核验的较小组合：`moss_image_sft_int8_convrot.safetensors` 5,413,698,958 B；`qwen3.5_9b_w4a8_gptq.safetensors` 7,343,591,088 B；`flux2-vae_small.safetensors` 249,521,340 B。三者共 **13.007 GB**，尚未算 LoRA 和运行时内存。[完整文件记录](https://huggingface.co/api/models/Comfy-Org/MOSS-Image?blobs=true)。应放于 `models/diffusion_models/`、`models/text_encoders/`、`models/vae/` 对应目录。此组合为 Comfy-Org 的量化版本，不是 OpenMOSS 的原始 BF16 目录。此处选 **SFT** 以匹配下述 8 步 LoRA。
- `lodestones` 的[8 步 DMD 项目](https://huggingface.co/lodestones/MOSS-Image-SFT-8-steps-dmd)为第三方蒸馏，基于 **SFT**，不是 Base；当前 Usage 建议将 `lora.safetensors`（1,189,176,800 B）以强度 1 直接交给 ComfyUI LoRA Loader。旧 `time_embedding.safetensors`、`dataspace.safetensors` 和数据空间采样算法整节已标为弃用，不应据此要求当前用户下载或采用它们。[当前 README 更新](https://huggingface.co/lodestones/MOSS-Image-SFT-8-steps-dmd/commit/f95df83b5e90ae91ea412434b3f9b7f1c8c6314f)。作者没有给出完整 sampler/scheduler/shift 配方；8 步、CFG 1 可作为候选，不能预先承诺精确复现。Comfy-Org SFT INT8 + 最小编码器/VAE + LoRA 合计约 **14.20 GB**，运行还需系统与激活内存；本机结果另见 trials 记录。

## 2. Kroma v0.3.1 Turbo

- 训练者的[模型卡](https://huggingface.co/lodestones/Kroma)推荐 `kroma-v0.3.1-turbo-opd.safetensors`，文件 **26,283,332,880 B**，SHA-256 `3cfb5bc847c804ea8e8f894677f7e16ebe4c9ff0f978896cc5e7eb1e64fc7d82`（[API](https://huggingface.co/api/models/lodestones/Kroma?blobs=true)）；另需 Krea 2 文本编码器和 VAE。训练者给出的 Turbo 设置为 **8–12 步、CFG 1.0–1.5、shift 1.15**。其模型卡的下载表仍写旧 `v0.2` 文件名，前面的 `v0.3.1` 推荐语是较新版本的依据。“4 步”并非训练者在模型卡给出的建议，可能来自其他工作流或作者调参，需要原文核验。
- 第三方 [Abiray 的 v0.3.1 GGUF](https://huggingface.co/Abiray/Kroma-v0.3.1-Turbo-OPD-GGUF)有 `Q2_K` 5,961,520,160 B（SHA-256 `4d2f6b26a54c5c3625ffcd0a3df8b7a840cb066d5293779a7d4ae630426503c3`），`Q3_K_S` 7,196,021,792 B（[API](https://huggingface.co/api/models/Abiray/Kroma-v0.3.1-Turbo-OPD-GGUF?blobs=true)）。Q2 已是明显牺牲精度的候选，不等于“6 GB 运行显存”。
- [Comfy-Org/Krea-2](https://huggingface.co/Comfy-Org/Krea-2)对应文本编码器 `qwen3vl_4b_fp8_scaled.safetensors` 5,242,467,968 B、VAE `qwen_image_vae.safetensors` 253,806,246 B（[API](https://huggingface.co/api/models/Comfy-Org/Krea-2?blobs=true)）。Kroma Q2 + 两个配件合计 **11.458 GB**，仅是硬盘上的文件大小。加载 CLIP 时必须选 `krea2` 类型。[city96 ComfyUI-GGUF 的 Krea 2 支持讨论](https://github.com/city96/ComfyUI-GGUF/issues/464)曾存在架构/视觉编码器识别问题，因此在当前 Windows AMD 环境中不能仅凭 GGUF 仓库的“目标显存”宣称可运行；需用独立环境核对插件版本并实测。

## 3. MiniMax H3 + BFS 角色替换

- 搜狗索引标题未声称 8 GB 可运行。这是**视频生成**，不应与前两项图像模型同列按“8G 可用”处理。[角色替换项目作者文档](https://huggingface.co/Alissonerdx/Minimax-H3-ComfyUI/blob/main/docs/character-swap.md)提供 v1.1 LoRA（80,673,112 B）和两种工作流：BFS Shot Planner 要求 ComfyUI-BFSNodes 1.113.0+，原生工作流可做单镜头。v1.1 文档可能晚于公众号 2026-10-14 的索引文章；文章或许讲 v1.0，只有原文能确认。v1.1 的 8 步设置还需 DMD Turbo LoRA。
- 其工作流要求 [Comfy-Org/MiniMax-H3](https://huggingface.co/Comfy-Org/MiniMax-H3)的 `ref2va` 扩散主模型、32B Qwen3-VL 编码器、视频及音频 VAE。较小的公开组合仍为：`minimax_h3_ref2va_pruned_int8_convrot.safetensors` **20,970,379,616 B**；`qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors` **15,687,142,551 B**；视频 VAE **5,207,808,496 B**；音频 VAE **605,254,808 B**（[API](https://huggingface.co/api/models/Comfy-Org/MiniMax-H3?blobs=true)）。仅这四项共 **42.47 GB**，尚未算角色 LoRA、Turbo LoRA、参考图描述模型和运行开销；该机器 16 GB RAM / 8 GB VRAM 不宜下载这套权重进行本地尝试。只下载 80 MB 角色 LoRA 也不能独立生成视频。
- [ComfyUI 官方 H3 指南](https://docs.comfy.org/tutorials/video/minimax/minimax-h3)说明原生节点支持和模型下载；BFS 是长视频规划扩展，非基础 H3 的必要依赖。对本机而言，先不安装 BFS，不下载 H3 大权重是资源约束下的结论；若以后有更多内存/GPU，再以短片段工作流验证。

## 本机试验顺序建议

1. 先在现有 ComfyUI 安装中检查 MOSS/Krea2 节点支持、已存的编码器/VAE，再决定下载的确切文件，避免重复占盘。
2. Kroma 可先尝试第三方 Q2 GGUF，但应先确认当前 ComfyUI-GGUF 是否能加载 Krea2；若不支持，暂停下载。即便支持，也需要逐阶段卸载并从低分辨率试起，实际内存和速度待实测。
3. MOSS 先尝试 Comfy-Org 的量化 SFT 或 Base，做 50 步基础图像，再添加第三方 8 步 LoRA 验证。其约 13–14 GB 文件集合接近 16 GB RAM，不能承诺成功。
4. H3 记录为当前硬件不适合本地尝试；若原文指出完全不同、显著更小的模型文件，再重新评估。

以上文件 API 记录的是核验时的 `main`：Comfy-Org/MOSS-Image `3284a1dbb351e3396d70f39f2a71cbf6ed2ef1bb`；lodestones/Kroma `94bfb29d748c0cd9319e7d9b489b7f9f3a6f6d92`；Abiray/Kroma-v0.3.1-Turbo-OPD-GGUF `4d022118e37efa85e14239818cfde7ddfcf44c69`；Comfy-Org/Krea-2 `1171f4dc7e325bf3734586942e737872506c73e1`；Comfy-Org/MiniMax-H3 `e5eb578a89295337b8ff433a035929ce0279e0b6`；Alissonerdx/Minimax-H3-ComfyUI `37d7d8b302ec4168ff30467c900c588db253cad9`。

下载验证清单（仓库、相对路径、体积见上；下列 SHA-256 可用于文件完成后的校验）：

- Kroma Q2 `4d2f6b26a54c5c3625ffcd0a3df8b7a840cb066d5293779a7d4ae630426503c3`；Krea 2 编码器 `54bd5144df0bbc25dd6ccadfcb826b521445a1b06ae5a42570bdd2974ca87094`；VAE `a70580f0213e67967ee9c95f05bb400e8fb08307e017a924bf3441223e023d1f`。
- MOSS SFT INT8 `b4d1475bc7eeffd7b809e82ea13a1fba1fb85c4e18365af3813722faa5c0fe4f`；W4A8 编码器 `4cc6a1543ad2061806da46f35f90cadb4801dcba246c44782cf42ec0feb6407c`；small VAE `d8d52ba036475f5fb07c8b435e176d3d97ebfa82f0d1a1c317f9cc1e25bd013b`。
