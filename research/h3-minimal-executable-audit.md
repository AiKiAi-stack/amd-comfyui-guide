# MiniMax H3 在 RX 6650 XT 8GB / 16GB RAM 上的最小可执行审计

准备核验：2026-10-19；2026-10-20 的实际成功诊断及限制见末节。下文准备阶段的假设不替代实测结果，BFS角色替换仍未验证。原生 [Comfy-Org H3 模板](https://github.com/Comfy-Org/workflow_templates/blob/main/templates/video_minimax_h3_r2v.json)使用32B文本编码器和约20.97GB的原生扩散权重；只按原文件大小判定16GB RAM绝对不能跑并不成立，因为ComfyUI有动态VRAM/卸载路径。这里另测更轻组合。

## 组件与来源

| 用途 | 固定来源与 revision | 文件 / bytes / SHA-256 |
|---|---|---|
| Ref2VA 扩散 | [molbal/MiniMax-H3-GGUF](https://huggingface.co/molbal/MiniMax-H3-GGUF/tree/b45874371c61c49bf04096602f5527aac71b360b) `b45874371c61c49bf04096602f5527aac71b360b` | `minimax-h3-ref2va-Q4_0.gguf`, 11,377,542,880, `737463c522b0f78ebe157df918c272935c2b61047ba7ae303008cfc84ba81644` |
| 视频 VAE | [Comfy-Org/MiniMax-H3](https://huggingface.co/Comfy-Org/MiniMax-H3/tree/e5eb578a89295337b8ff433a035929ce0279e0b6) `e5eb578a89295337b8ff433a035929ce0279e0b6` | `vae/minimax_h3_video_vae_int8_convrot.safetensors`, 2,811,065,184, `52a2c8c73583c86e4f41cdcce3a6ad0ea562987bc0bf3d60a0cef5f5c8e60c0e` |
| 小编码器到 32B 条件空间投影 | [NicoLab28/ClipProj-MiniMax-H3](https://huggingface.co/NicoLab28/ClipProj-MiniMax-H3/tree/2ebdbcdc27a29a9607efdb221a9afcb9a0cdd808) `2ebdbcdc27a29a9607efdb221a9afcb9a0cdd808` | `mmh3-4b-ClipProj-v3.1.safetensors`, 26,256,128, `0184e5c8d666a131962506d21949c2d8a8c6f33445b7b5e347e9a7e0a5baa819` |
| 文本/图像编码器，复用现有文件 | [Comfy-Org/Krea-2](https://huggingface.co/Comfy-Org/Krea-2/tree/1171f4dc7e325bf3734586942e737872506c73e1) `1171f4dc7e325bf3734586942e737872506c73e1` | `qwen3vl_4b_fp8_scaled.safetensors`, 5,242,467,968, `54bd5144df0bbc25dd6ccadfcb826b521445a1b06ae5a42570bdd2974ca87094`；已在主 ComfyUI `models/text_encoders`，隔离安装只读引用 |

四文件共 19,457,332,160 bytes（磁盘体积，不等于同时占用 RAM）。新增下载 14,214,864,192 bytes，三份下载的源 revision、最终字节数和完整 SHA-256 均记录在 `trials/2026-10-19-h3/{model,vae,clipproj}.verified.json`。官方 VAE 比 Kijai 的同名实验 VAE 小 360,605,728 bytes，且[官方 Ref2VA 模板](https://github.com/Comfy-Org/workflow_templates/blob/main/templates/video_minimax_h3_r2v.json)直接指定它。D 盘有约 193GB 空闲，因此磁盘容量不是限制。真正未知的是 Windows ROCm 7.14 在 RX 6650 XT 上的动态卸载、4B 视觉编码、Q4_0 反量化和 H3 VAE 在 16GB RAM / 8GB VRAM 内的峰值、页面文件压力、耗时及图像是否正确。上游模型卡标明 Ref2VA 正常输出约 **4–15 秒**；5 帧仅约 0.2 秒，超出训练/产品时长范围，必须只用作加载、采样、解码诊断，不做画质或角色一致性结论。

## 独立环境与诊断图

- 主 ComfyUI 保持不动。`h3-sandbox/ComfyUI` 是从主 ComfyUI commit `ce1e922d8623bb507180e32a0c01a7d0e29edef7` 创建的 detached Git worktree；仅含两个隔离自定义节点：[molbal/ComfyUI-GGUF](https://github.com/molbal/ComfyUI-GGUF) commit `b07c7e0437eeb4b2dab6e96509cbb8efdabf1b01` 与 [nicolab28/ComfyUI-ClipProj](https://github.com/nicolab28/ComfyUI-ClipProj) commit `c01ba8fb8f41b4f2094dbd0b185cdc238fb6134c`。当前共享 `.venv` 仅被调用、未安装/修改；已有 `gguf 0.19.0`、`comfy-kitchen 0.2.38`，满足插件的强制依赖，ClipProj 无新增依赖。
- 插件 fork 的 [README](https://github.com/molbal/ComfyUI-GGUF#supported-conversion-formats) 明列 H3 和 `Q4_0`；其 `UnetLoaderGGUFDynamicVRAM` 是为低显存加载选用的节点。没有拿其他 GGUF 项目的更小 Q2_K 文件冒充可用组合，因为缺与此插件/模型明确匹配的文件与验收证据。
- ClipProj 作者的 [单卡建议](https://github.com/nicolab28/ComfyUI-ClipProj#one-gpu-or-not-much-vram-use-the-stock-loader)是原生 `CLIPLoader(type=krea2)` 接 `ClipProjApply`，使编码器可由 ComfyUI 卸载；不用会常驻显存的 all-in-one loader。已有 4B fp8 Qwen3-VL 由 `extra_model_paths.yaml` 从主目录只读共享。
- 诊断图：[ref2va-5frame-api.json](../trials/2026-10-19-h3/ref2va-5frame-api.json)使用 384×256、5 帧、4 步 `res_multistep/simple`、一个自制 cyan robot 参考图；`VAEDecode` 同批输出保存无声 WebP 和逐帧 PNG。参考图 API 输入用 `ref_images.ref_image_0`，这是 [ComfyUI 问题 #15667](https://github.com/Comfy-Org/ComfyUI/issues/15667)说明的正确点号形式；嵌套 `ref_images` 会被忽略。视频 VAE 与参考图编码都会经过图，音频 VAE 在此无声诊断中省略。
- 这 **4 步且无 LoRA** 只用于触发模型加载和采样，**不是官方可用画质配方**。所存 [官方 Ref2VA 模板](../trials/2026-10-19-h3/official-r2v-reference.json)的默认开关是无 LoRA、`res_multistep/simple`、**20 步**；另有可切换的 4 步分支，需要 `minimax_h3_ref2v_turbo_4step_v0.1_comfyui_bf16.safetensors`（[Comfy-Org 模型仓库](https://huggingface.co/Comfy-Org/MiniMax-H3/tree/e5eb578a89295337b8ff433a035929ce0279e0b6)，1,956,193,000 bytes），目前未下载。若诊断成功，正式短片段先按默认 20 步测试，或另行加入并验证该 LoRA。
- 独立启动器 `h3-sandbox/start-h3.ps1` 绑定 `127.0.0.1:8189`，输入/输出/日志/user/temp在 `trials/2026-10-19-h3`。准备时采用CPU VAE；实际成功配置改为GPU FP16 VAE并预留2GB显存，见末节。提交器 `h3-sandbox/submit-diagnostic.ps1` 保存 `/prompt` 返回的id。

## 与 BFS 角色替换及其他 H3 功能的关系

[角色替换作者的 v1.1 文档](https://huggingface.co/Alissonerdx/Minimax-H3-ComfyUI/blob/main/docs/character-swap.md)明确要求 **Ref2VA** 扩散模型、`MiniMaxH3ReferenceToVideo` 的 `<Picture 1>` 人物参考，以及 `MiniMaxH3AddGuide(frame_idx=0)` 的原视频引导；此功能**不要求 FL2VA 权重**。因此本次 Q4_0 是同一个 **Ref2VA 任务变体**，但**不是作者工作流里精确的原生 checkpoint**：作者指定 `minimax_h3_ref2va_pruned_int8_convrot.safetensors`（[Comfy-Org](https://huggingface.co/Comfy-Org/MiniMax-H3)，20,970,379,616 bytes）。Q4_0 与作者的角色 LoRA、DMD LoRA 能否正确映射到 pruned 权重，尚无本机/上游组合验证；5 帧诊断即使成功，也只能形成单独的 `Ref2VA diagnostic` 结果，不能算角色替换成功。

若要**精确复现** v1.1 的 8 步角色替换工作流，还需下载但本轮暂不下载：作者角色 LoRA `loras/minimax_h3_character_swap_v1.1_ref2va_fro.safetensors`（[Alissonerdx 仓库](https://huggingface.co/Alissonerdx/Minimax-H3-ComfyUI)，80,673,112 bytes）、`experimental/minimax_h3_dmd_ref2va_8step_turbo_pruned.safetensors`（[drbaph 仓库](https://huggingface.co/drbaph/MiniMax-H3-Turbo-Lora-ComfyUI)，2,285,989,092 bytes）、上面的官方 pruned Ref2VA 模型、官方 32B 编码器 `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors`（15,687,142,551 bytes），以及作者指定的 FP16 视频 VAE（5,207,808,496 bytes）和 FP32 音频 VAE（605,254,808 bytes）。工作流还默认用 9B 视觉语言模型 `qwen3.5_9b_w4a8_gptq.safetensors`（[Comfy-Org/MOSS-Image](https://huggingface.co/Comfy-Org/MOSS-Image)，7,343,591,088 bytes）自动描述参考人物；手工写描述或使用其他兼容模型可替代该步骤。BFS 长视频工作流另需 `ComfyUI-BFSNodes` 1.113.0+，单镜头可用作者提供的原生节点工作流。

H3 家族还有 FL2VA（首帧/末帧条件）、Ref2VA（多模态参考）等不同权重。若“续写”实际指首末帧续接，不能直接把这张 Ref2VA 诊断图算作该功能；需按对应工作流另核对 FL2VA 权重、引导输入与输出后再试。

## 继续的验收顺序

1. 等当前模型任务完全释放 GPU/RAM。三份 `.verified.json` 已存在；若今后文件有变动，运行 `h3-sandbox/download-verified.ps1` 可续传并重新校验。启动前再做纯 CPU 导入/节点注册检查。之前 CPU quick-test 在日志确认 `Device: cpu` 后因主测试仅剩约 2GB RAM 而主动停止；静态 `compileall` 和 JSON 解析已通过，不应把它称为完整导入验证。
2. 在 PowerShell 运行 `& 'D:/AI/comfyui-rx6650xt-lab\h3-sandbox\start-h3.ps1'`，检查 `http://127.0.0.1:8189/object_info` 是否同时列出 `UnetLoaderGGUFDynamicVRAM`、`ClipProjApply`、`MiniMaxH3ReferenceToVideo`，然后在另一终端运行 `& 'D:/AI/comfyui-rx6650xt-lab\h3-sandbox\submit-diagnostic.ps1'`。先记录 `/prompt` 接受/拒绝与节点错误，再记录峰值 RAM/VRAM、页文件、耗时、日志和是否生成 WebP 与 5 张 PNG；实际图像内容需目视确认。
3. 若 5 帧诊断成功，再做更有意义的 124 帧/24fps（约 5.2 秒）低分辨率参考生成；这一步资源需求会显著高于诊断，应单独观察并可中止。只有这一层产生可用视频，才进入 BFS 角色替换项目和 LoRA 兼容性验证。`Alissonerdx/Minimax-H3-ComfyUI` 的 [角色替换文档](https://huggingface.co/Alissonerdx/Minimax-H3-ComfyUI/blob/main/docs/character-swap.md)使用 80MB LoRA 与 BFS；该 LoRA 在 GGUF fork 上的映射未被验证，故此组合不能先宣称实现了角色替换。

文件下载的最终状态、哈希及能否启动服务，以同目录 `.verified.json` 和实际日志为准。首次切换 VAE 来源时留有约 1.5 MB 的 `minimax_h3_video_vae_int8_convrot.safetensors.kijai-abandoned.part` 隔离残片；它不被模型节点加载，后续可在确认全部试验状态后清理。

## 2026-10-20 真实诊断结果（后续追加）

上述准备阶段的“未运行”记录现已有后续实测：`trials/2026-10-19-h3/diagnostic-gpu-vae-native-reserve2-result.json` 记录一次 **success**，完整往返 433.08 秒；同次 [API 图](../trials/2026-10-19-h3/diagnostic-gpu-vae-native-reserve2-api.json)仍为 384×256、5 帧、4 步、无 DMD，使用 Q4_0 Ref2VA、4B fp8 + ClipProj，但把视频 VAE 改为 `minimax_h3_video_vae_fp16.safetensors`。该次 [进程参数](../trials/2026-10-19-h3/diagnostic-gpu-vae-native-reserve2-process.json)是 GPU VAE（**没有** `--cpu-vae`）、`--disable-async-offload --lowvram --reserve-vram 2.0`；不能把此成功直接归因于本报告上面的 INT8 VAE/CPU VAE 启动器。日志中的 ComfyUI prompt 耗时为 346 秒。

只读复核了同次 `/prompt` 返回的 `prompt_id=94e6c992-6339-4037-aed5-d45dfcaa21f6`、[history](../trials/2026-10-19-h3/diagnostic-gpu-vae-native-reserve2-history.json) 的 `execution_success`，节点 14 列出 5 张 384×256 PNG，节点 13 列出同批 animated WebP；六个实际输出的字节数与 SHA-256 均与 result receipt 一致。系统监测峰值已用 RAM 15,234,715,648 B、swap 605,536,256 B、服务 private bytes 10,435,297,280 B、采样统计 VRAM 已用峰值 5,199,883,776 B。此前未预留显存的 native 运行在 sampler OOM，故 `reserve-vram 2.0` 是本次成功配置的实际差异之一，尚不能单独归因或泛化。

这证明该机能完成一次极短的 Ref2VA **技术诊断**；5 帧/4 步仍超出模型正常输出时长且没有 DMD，不代表角色替换、续写或可用画质。正式功能需另做正确时长、正确 checkpoint/LoRA/引导素材的输出验收。

## 2026-10-20 实测补充：五帧诊断已通过

[最新结果](../trials/2026-10-19-h3/diagnostic-gpu-vae-native-reserve2-result.json)为success，prompt id为 `94e6c992-6339-4037-aed5-d45dfcaa21f6`，包含服务启动共433.08秒。使用原Q4_0与4B ClipProj组合，但换成官方未量化 `minimax_h3_video_vae_fp16.safetensors`（5,207,808,496 bytes，SHA-256 `7c1f131492e7eddacaac9069a61b81bdd39de5cc96561e677c5eab1cdce5e522`），VAE在GPU，`--reserve-vram 2.0`、同步卸载、未启用INT8 fallback。原INT8 VAE的HIPBLAS错误、CPU解码主动中止，以及FP16未预留显存时的采样OOM均保留。

五张384×256 PNG的嵌入节点类别/输入已与实际api.json逐一核对，另有五帧无声WebP。首尾帧可见青色机器人与洋红围巾，画面相似；五帧约0.2秒，不据此认定动作流畅、正常时长质量或BFS功能。系统已用RAM采样峰值约14.19GiB，Comfy API显存采样峰值约4.84GiB；它们不是所有瞬时分配的精确峰值。

重跑该诊断：先释放其他GPU队列，运行 `h3-sandbox/start-h3.ps1 -GpuVae -ReserveVram 2.0`；8189就绪后在另一终端运行 `h3-sandbox/submit-diagnostic.ps1 -NativeVae`。实际图、命令与history也保存于 [功能对照卡](../trials/2026-10-19-features/cases/ref2va-5frame-diagnostic/)。正式20步、正常帧数以及BFS五项功能仍未验收。
