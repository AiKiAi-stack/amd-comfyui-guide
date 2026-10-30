# 刘悦博客索引中五组 ComfyUI 模型：RX 6650 XT 本机试验

试验日期：2026-10-19（Asia/Shanghai）。公众号原文不可访问；五组名称来自公开搜索索引，不能确认文内实际下载链接与这里所选权重相同。来源核验见 [`research/liuyue-comfyui-models-2026-10-18.md`](../../docs/reference/research/liuyue-comfyui-models-2026-10-18.md) 和 [`research/liuyue-five-model-trial-sources.md`](../../docs/reference/research/liuyue-five-model-trial-sources.md)。

本机：Windows、AMD Radeon RX 6650 XT（ComfyUI 报告 8,176 MB VRAM）、16,197 MB RAM；ComfyUI 0.41.0，PyTorch 2.12.0+rocm7.14.0，原有环境未替换。模型及试验文件均位于 D:。既有 Qwen-Image-2.1 基础版 768 像素文生图曾在本机完成，输出为 `ComfyUI/output/QwenImage21_RX6650XT_768_00001_.png`。

下载由 `download_weights.py` 使用固定 HF revision、预期字节数和 SHA-256 核验；`.part` 可续传，最终文件出现前不可提交工作流。`*-download.json` 是可复现清单，`*.verified.json` 是完成校验的凭据。本轮新增 **10 个权重文件，共 36,299,894,784 B（约 36.30 GB）**，全部有完成校验凭据。原有 Qwen 基础版三份权重未重复下载。下载日志和 ComfyUI 任务/历史 JSON 存于此目录。

已构造五组试验图：`qwen-base-edit-api.json` 是第一次 768 像素参考图编辑，`qwen-base-edit-512-api.json` 为第二次 512 像素、15 步重试（没有局部遮罩）；`qwen-turbo-api.json` 用普通 Turbo GGUF + 原有编码器，以官方 8 步 sigmas、512×512 测底层兼容；`qwen-turbo-un-api.json` 把编码器换为 AtomicChat 的 Uncensored GGUF，并配视觉投影文件；`kroma-api.json` 用 Q2 GGUF 做 512×512、4 步测试；`moss-api.json` 用 SFT INT8 做 512×512、50 步基础测试。每组完成与否以对应 `*-history.json` 和输出图片为准；单有任务提交或权重下载不算运行成功。

特别注意：AtomicChat 的 Turbo-Uncensored 仓库修改的是 **Qwen3-VL 文本编码器**，不是 Turbo 扩散主模型；其模型卡明确表示在图片试验中没有测到解除限制的效果。其 GGUF 最初在 stable-diffusion.cpp 验证，ComfyUI 能否加载需本机结果判断。

MOSS 第三方 8 步 DMD 的当前模型卡建议直接将 `lora.safetensors` 以强度 1 加载进 ComfyUI，旧数据空间算法、时间嵌入替换等整节已标为 `[Deprecated] ignore this section`，不应作为当前必要条件。模型卡没有明示完整 KSampler 配方；本轮候选用 8 步、CFG 1、Euler/sgm_uniform、shift 5，除步数和 no-CFG 外，其余沿用 SFT 基础设置。其与作者图片的精确复现、INT8 组合兼容性仍需实测。详见 `research/moss-8step-workflow-audit.md`。

## 已观察到的运行结果

- Qwen-Image-2.1 基础版 768 像素参考图编辑于 09:23 提交，ComfyUI 在加载 GGUF 后、采样 0/25 处发生 Windows `access violation`，见 `comfy.stderr.log` 第 75 行附近，栈指向 `ComfyUI-GGUF/ops.py` 的 `.to` 与 Qwen 注意力调用。未生成编辑图。此时普通 Turbo 任务尚在队列中，服务器崩溃使它没有执行。
- 重启 ComfyUI 并添加 `--disable-async-offload` 后，普通 Turbo 的 512×512、8 步任务成功，用时 **652.78 秒**（含冷加载，约 10 分 53 秒）。证据：`qwen-turbo-history.json`；输出 `ComfyUI/output/Liuyue_Qwen21_Turbo_RX6650XT_00001_.png`。视觉检查：完整白猫、雨窗与霓虹街景，未见黑图或噪声图。
- 随后的基础版参考图编辑在 512×512、15 步下成功，用时 **423.46 秒**（约 7 分 3 秒，部分组件已缓存）。证据：`qwen-base-edit-512-history.json`；输出 `ComfyUI/output/Liuyue_Qwen21_Base_Edit_RX6650XT_00001_.png`。视觉检查：原始橘猫变成白猫，姿态、街景、窗户与整体构图基本保留；分辨率与毛发细节发生变化。尚未验证遮罩重绘或多参考图。
- Turbo-Un 编码器组合随后触发第二次 Windows `access violation`：`comfy-retry.stderr.log` 第 109 行，栈为 `model_patcher.partially_unload -> GGUF ops.py .to`，之前出现 `Attempting to release mmap`。没有生成 UN 输出。这也表明仅关闭异步卸载不能解决全部 GGUF 编码器卸载问题。
- Kroma 和 MOSS 当时尚在队列中，服务器退出导致未执行；不计为模型运行失败。之后所有必需文件均已校验完成。
- Kroma v0.3.1 Turbo Q2 GGUF 在独立服务内完成 **512×512、4 步、CFG 1、Euler/simple**，总用时 **285.03 秒**（含冷加载，约 4 分 45 秒），其中 4 步采样日志约 **17.8 秒**。证据：`kroma-history.json` 与 `comfy-trial3.stderr.log`；输出 `ComfyUI/output/Liuyue_Kroma031_Q2_4step_RX6650XT_00001_.png`。视觉检查：狐狸、苔石、雾林与提示词相符，未见黑图或明显噪声。此结果只覆盖 Q2、该分辨率和文生图，未验证多参考、换脸或较高精度权重。
- MOSS 首次独立 50 步测试在 **0/50 的主模型 QKV INT8 线性层**报 `HIPBLAS_STATUS_INVALID_VALUE`；文本编码器已通过。日志另有 gfx1032 的 `TensileLibrary_lazy_gfx1032.dat` / `.hsaco` 缺失信息。证据：`moss-int8-error-history.json` 和 `comfy-moss.stderr.log`，此任务无输出。
- 为重试加入 `ComfyUI/custom_nodes/gfx1032_quant_fallback/__init__.py`：仅当进程环境变量 `COMFY_GFX1032_INT8_FALLBACK=1`、HIP 且 GPU 为 gfx1032 时，将 ComfyUI 的 INT8 计算能力检测置为不支持，让其使用已有量化格式解量化计算回退。权重仍按量化格式存储，核心文件未修改。关闭此环境变量即不启用；默认无效。该路径经 Luna（Max）只读代码复核，并由以下实际出图验证。
- 开启回退后的第一张 MOSS 图虽然执行完 50 步并返回 API success，但视觉检查是纹理噪声，**不算模型可用**。已发现工作流节点错误：核心 MOSS 默认 `sampling_settings.multiplier=1.0`，通用 `ModelSamplingSD3` 节点却覆盖为 1000。已改为 `ModelSamplingAuraFlow`（multiplier 1.0、shift 5）再试；原始错误图与 history 保留为证据，`moss-wrong-timestep-noise-history.json` 对应 `Liuyue_MOSS_SFT_INT8_50step_RX6650XT_00001_.png`。
- **修正后的 MOSS SFT INT8 50 步成功**：512×512、CFG 3、Euler/sgm_uniform、AuraFlow shift 5、SLG 第 22 层，启用 gfx1032 INT8 回退。用时 **198.197 秒（约 3 分 18 秒，组件已缓存）**。证据 `moss-history.json`，正确输出为 `ComfyUI/output/Liuyue_MOSS_SFT_INT8_50step_RX6650XT_00002_.png`。视觉检查：完整宇航员、丛林、阳光，符合提示词。
- **MOSS 8 步 LoRA 候选也成功**：相同 prompt/seed/512×512，LoRA 强度 1、CFG 1、Euler/sgm_uniform、AuraFlow shift 5，不加 SLG；启用相同回退。用时 **187.575 秒（约 3 分 8 秒，含本次 LoRA 初始化）**，初始化后剩余采样日志约 62 秒。证据 `moss8-history.json`，输出 `ComfyUI/output/Liuyue_MOSS_SFT_DMD_INT8_8step_RX6650XT_00001_.png`。视觉检查：完整宇航员和丛林，无黑图或纹理噪声。此为基于作者当前 Usage 的候选参数实测，未声称与作者未公布的完整采样配方精确一致。

收尾检查：本机 `http://127.0.0.1:8188` 服务保留可访问，当前为启用 gfx1032 回退的进程；任务队列为空，已请求释放模型与测试内存。此次验证覆盖 512 像素图像生成和单张参考图编辑，不包含视频、多参考人物身份保持或遮罩重绘。公众号正文仍未读取，不能确认这组公开权重等于作者整合包的实际文件。

GPT-6 Luna（Max）只读复核确认：两个崩溃都进入 `GGMLTensor.to()`，但首次是注意力中的张量搬运，第二次是腾显存时的部分卸载。GGUF loader 通过 `GGUFReader` 和 `torch.from_numpy(tensor.data)` 保留 mmap 数据；插件也有通过设备搬运解除 mmap 链接的代码。因此 mmap 张量与设备搬运的交互是排查线索，尚不能证明 `fast-disk` 或 DynamicVRAM 是根因。关闭 `fast-disk` 也不会关闭 GGUF 自身的 mmap。相关上游旁证：[GGUF #444](https://github.com/city96/ComfyUI-GGUF/issues/444)、[ComfyUI #14142](https://github.com/Comfy-Org/ComfyUI/issues/14142)，均不等于本机问题已被上游复现。


