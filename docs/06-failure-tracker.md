# 出图失败追踪 · 2026-10-21

以本机原始实验和上游问题交叉整理。旧案例保留原始状态；独立进程成功不计为连续出图修复。代码在 `fix/gguf-repeat-stability` 分支管理，模型和原始日志留在本地。

## BC-001 · Z-Image 双 GGUF 连续出图原生退出 · 本轮未复现，根因未解决

首张成功；第二张改变提示词，重新请求 ZImageTEModel 时，在 `GGMLTensor.to → Module._apply → partially_unload` 原生退出，`0xC0000005`，无第二张图片。

- [历史失败摘要](../trials/2026-10-20-zimage/cases/zimage-gguf-prompt-change/attempts/001-native-access-violation/attempt-summary.json)
- [历史实测与独立服务成功边界](../trials/2026-10-20-zimage/README.md)
- 新复现命令：`scripts/repro_gguf_repeat.py`，一个服务依次改变提示词与 seed，要求每张均有成功 history 和可解码 PNG；保留失败 history、图和进程退出码。实际图片另行目视检查。
- 上游 [GGUF #444](https://github.com/city96/ComfyUI-GGUF/issues/444) 与 [未合并 PR #445](https://github.com/city96/ComfyUI-GGUF/pull/445) 讨论卸载时 mmap 权重访问冲突。其触发点为 `unpatch_model`，本机历史栈为 `partially_unload`，尚不能认定同一根因。
- PR #445 曾有 LoRA 强度变化回归，不能直接把 `unpatch_weights=False` 当作完整修复。
- 本轮三组各复用单一进程，3/3、3/3、5/5 均通过，合计 11 张，均完成图片检查。预留 2GB 与不额外预留均通过，不能将该参数认定为根因；[完整实测与重跑方法](../trials/2026-10-21-gguf-repeat/README.md) 保留了每次实际工作流、图片、history 摘要和 SHA。

## BC-002 · Qwen GGUF 重载崩溃 · 待独立回归

[历史失败](../trials/2026-10-20-qwen-uncensored/attempts/q21-un-gothic-horror-gguf-reload-crash/result.json) 记录了 GGUF 重载访问冲突。CPU 编码、关闭前缀缓存和独立服务是历史规避方法。Z-Image 修复若有效，仍须单独测试 Qwen，不能自动标记已修复。

## BC-003 · MOSS INT8 首步 HIPBLAS 失败 · 已有规避，待回归

gfx1032 INT8 路径报 `HIPBLAS_STATUS_INVALID_VALUE`。已有 [显式启用的浮点回退节点](../code_source/gfx1032_quant_fallback/__init__.py)，属于绕过不支持算子，不是修复 AMD 原生 kernel。

## BC-004 · MOSS 返回成功但全是噪声 · 本轮增加入口防回归

错误的 `ModelSamplingSD3` timestep multiplier 与模型不符；历史实验改为 `ModelSamplingAuraFlow`、multiplier 1、shift 5 后出图。见 [故障说明](04-troubleshooting.md)。本轮已在 [重跑入口](../scripts/replay_workflow.py) 增加针对已测 MOSS SFT 文件的检查：沿实际采样模型链寻找生效的时间尺度覆盖，在联网/提交之前拒绝已知错误配置，提示正确节点与 shift。不会自动重写用户工作流，也不会拦截普通 SD3 模型。

[回归测试](../scripts/test_workflow_checks.py) 使用历史噪声工作流、修正后的 SFT/8步工作流，以及无关模型、断开分支和环路。入口测试先观察到失败（旧入口尝试联网，没有识别错误），应用检查后 5/5 通过。这证明提交前防护生效；本轮未重新生成 MOSS 图片，历史成功图不冒充新结果。

## BC-005 · Kroma 参考图节点内部升至 1024 导致 OOM · 降规格规避

512 输入不代表内部参考潜空间仍是 512。历史上改为显式 `VAEEncode + ReferenceLatent` 512 后出图，原 1024 路径未修复。见 [保留的原失败](../trials/2026-10-19-features/attempts/kroma-ref1024-20261019-160446/kroma-multiref/result.json)。

## BC-006 · FLUX.2 关闭锁页内存后出噪声 · 历史对照有效

本机移除 `--disable-pinned-memory` 后文生图及编辑恢复；[原失败图和成功对照](../trials/2026-10-20-flux2-klein/README.md) 均保留。底层 HIP/WDDM 原因未确认。上游 [#16337](https://github.com/Comfy-Org/ComfyUI/issues/16337) 也报告 AMD 动态显存噪声，但显卡不同，且其锁页开关对照结论不同，不能合并为一个通用故障。

## BC-007 · H3 采样阶段反量化 OOM · 小诊断通过，大任务未修复

历史 OOM 位于采样器权重反量化/clone，不能归类为 VAE 解码失败。后来的 [五帧诊断](../trials/2026-10-19-features/cases/ref2va-5frame-diagnostic/result.json) 成功仅证明极小链路可执行。正常视频任务仍需独立验收。

## BC-008 · ROCm 7.2 在 GPU 初始化时原生崩溃 · 未修复

旧隔离环境在 `torch.cuda.is_available()` 即访问冲突。当前工作环境是 torch 2.12.0 + ROCm 7.14，不能用其成功覆盖旧环境失败。先执行 [GPU 最小检查](../scripts/check_gpu.py)，再加载模型。

## BC-009 · 已移除的启动参数 · 历史启动错误

Z-Image 失败日志还保留一次 `unrecognized arguments: --normalvram`；这发生在启动阶段，与第二张图崩溃不同。当前复现脚本以默认 NORMAL_VRAM 加 `--disable-dynamic-vram`，不传该失效参数。上游 [启动参数说明](https://github.com/Comfy-Org/docs/blob/main/development/comfyui-server/startup-flags.mdx) 可用于核对，实际安装版本的 `--help` 才是本地依据。
