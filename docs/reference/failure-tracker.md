# 出图失败追踪 · 2026-10-21

以本机原始实验和上游问题交叉整理。旧案例保留原始状态；独立进程成功不计为连续出图修复。代码在 `fix/gguf-repeat-stability` 分支管理，模型和原始日志留在本地。

这份清单主要记录运行故障，不能代表全部功能完成度。

## BC-001 · Z-Image 双 GGUF 连续出图原生退出 · 本轮未复现，根因未解决

首张成功；第二张改变提示词，重新请求 ZImageTEModel 时，在 `GGMLTensor.to → Module._apply → partially_unload` 原生退出，`0xC0000005`，无第二张图片。

- [历史失败摘要](../../evidence/2026-10-20-zimage/cases/zimage-gguf-prompt-change/attempts/001-native-access-violation/attempt-summary.json)
- [历史实测与独立服务成功边界](../../evidence/2026-10-20-zimage/README.md)
- 新复现命令：`scripts/repro_gguf_repeat.py`，一个服务依次改变提示词与 seed，要求每张均有成功 history 和可解码 PNG；保留失败 history、图和进程退出码。实际图片另行目视检查。
- 上游 [GGUF #444](https://github.com/city96/ComfyUI-GGUF/issues/444) 与 [未合并 PR #445](https://github.com/city96/ComfyUI-GGUF/pull/445) 讨论卸载时 mmap 权重访问冲突。其触发点为 `unpatch_model`，本机历史栈为 `partially_unload`，尚不能认定同一根因。
- PR #445 曾有 LoRA 强度变化回归，不能直接把 `unpatch_weights=False` 当作完整修复。
- 本轮三组各复用单一进程，3/3、3/3、5/5 均通过，合计 11 张，均完成图片检查。预留 2GB 与不额外预留均通过，不能将该参数认定为根因；[完整实测与重跑方法](../../evidence/2026-10-21-gguf-repeat/README.md) 保留了每次实际工作流、图片、history 摘要和 SHA。

## BC-002 · Qwen GGUF 重载崩溃 · 待独立回归

[历史失败](../../evidence/2026-10-20-qwen-uncensored/attempts/q21-un-gothic-horror-gguf-reload-crash/result.json) 记录了 GGUF 重载访问冲突。CPU 编码、关闭前缀缓存和独立服务是历史规避方法。Z-Image 修复若有效，仍须单独测试 Qwen，不能自动标记已修复。

## BC-003 · MOSS INT8 首步 HIPBLAS 失败 · 已有规避，待回归

gfx1032 INT8 路径报 `HIPBLAS_STATUS_INVALID_VALUE`。已有 [显式启用的浮点回退节点](../../code_source/gfx1032_quant_fallback/__init__.py)，属于绕过不支持算子，不是修复 AMD 原生 kernel。

## BC-004 · MOSS 返回成功但全是噪声 · 本轮增加入口防回归

错误的 `ModelSamplingSD3` timestep multiplier 与模型不符；历史实验改为 `ModelSamplingAuraFlow`、multiplier 1、shift 5 后出图。见 [故障说明](../tutorial/07-troubleshooting.md)。本轮已在 [重跑入口](../../scripts/replay_workflow.py) 增加针对已测 MOSS SFT 文件的检查：沿实际采样模型链寻找生效的时间尺度覆盖，在联网/提交之前拒绝已知错误配置，提示正确节点与 shift。不会自动重写用户工作流，也不会拦截普通 SD3 模型。

[回归测试](../../scripts/test_workflow_checks.py) 使用历史噪声工作流、修正后的 SFT/8步工作流，以及无关模型、断开分支和环路。入口测试先观察到失败（旧入口尝试联网，没有识别错误），应用检查后 5/5 通过。这证明提交前防护生效；此处描述的是入口检查提交；后续已有独立 MOSS FP16 重试图片，风格验收仍见功能清单。

## BC-005 · Kroma 参考图节点内部升至 1024 导致 OOM · 降规格规避

512 输入不代表内部参考潜空间仍是 512。历史上改为显式 `VAEEncode + ReferenceLatent` 512 后出图，原 1024 路径未修复。见 [保留的原失败](../../evidence/2026-10-19-features/attempts/kroma-ref1024-20261019-160446/kroma-multiref/result.json)。

## BC-006 · FLUX.2 关闭锁页内存后出噪声 · 历史对照有效

本机移除 `--disable-pinned-memory` 后文生图及编辑恢复；[原失败图和成功对照](../../evidence/2026-10-20-flux2-klein/README.md) 均保留。底层 HIP/WDDM 原因未确认。上游 [#16337](https://github.com/Comfy-Org/ComfyUI/issues/16337) 也报告 AMD 动态显存噪声，但显卡不同，且其锁页开关对照结论不同，不能合并为一个通用故障。

## BC-008 · ROCm 7.2 在 GPU 初始化时原生崩溃 · 未修复

旧隔离环境在 `torch.cuda.is_available()` 即访问冲突。当前工作环境是 torch 2.12.0 + ROCm 7.14，不能用其成功覆盖旧环境失败。先执行 [GPU 最小检查](../../scripts/check_gpu.py)，再加载模型。

## BC-009 · 已移除的启动参数 · 历史启动错误

Z-Image 失败日志还保留一次 `unrecognized arguments: --normalvram`；这发生在启动阶段，与第二张图崩溃不同。当前复现脚本以默认 NORMAL_VRAM 加 `--disable-dynamic-vram`，不传该失效参数。上游 [启动参数说明](https://github.com/Comfy-Org/docs/blob/main/development/comfyui-server/startup-flags.mdx) 可用于核对，实际安装版本的 `--help` 才是本地依据。

## BC-010 · Qwen 反推词表临时内存与量化文本卸载 · 有端到端规避，根因未全修

CPU 原失败的 2,489,319,424 字节来自 `151936×4096` 输出层的全词表 float32 反量化。[可选分块插件](../../code_source/cpu_chunked_logits/bounded.py) 限制为每次 2048 行；[真实调用路径回归](../../scripts/test_chunked_logits.py) 未启用时触发 4099 行预算异常，启用后数值匹配完整 Linear。它不减少整个模型的基础内存，也不修复其他层的内存问题。

大模型 GPU 反推已产生准确 caption，但直接接出图仍在 `QuantizedTensor._handle_to → partially_unload` 原生退出。之后使用 [条件归档](../../code_source/repair_conditioning/__init__.py) 和 [分阶段运行器](../../scripts/run_conditioned_repair.py)，编码进程退出再开始采样，实际自动 caption→编码→15 步→CPU VAE→PNG 全部完成并目视通过。见 [完整尝试与图片](../../evidence/2026-10-21-repairs/README.md)。

这是流程规避，不是修复 native unload；原 CPU 配置仍慢且未完整验收。另一次静态 caption 的 CPU 编码续跑先在采样中 OOM，清理时再原生退出，不能把所有栈都归成同一个 GGUF 问题。原始失败与人工保护性停止分别保留。

## BC-011 · 多参考批次与 BFS 解码时 commit 耗尽 · 分阶段规避已出图

Qwen 双参考使用 legacy 编码时先触发 Windows commit 保护；原生动态显存编码完成五项。采样服务的第二项仍可能触发保护，即使使用 `--cache-none`，不能把缓存开关称作跨案例内存修复。当前采用每项独立采样进程，并记录实际 cache 设置。

BFS FP16 重试完成 15/15 步，却在 CPU VAE 加载时触发保护，没有 PNG。新增 `SaveRepairLatent/LoadRepairLatent` 后，采样归档并退出，再用独立 CPU 进程解码，得到完整图片。[结果与三阶段绑定](../../evidence/2026-10-21-repairs/cases/qwen-bfs-direction-mask/result.json) 留有采样/编码/解码 API 和归档 SHA；视觉仍部分达到，运行完成不等于精确身份复现。

归档测试检查 dtype、noise mask 与原值精确往返；图测试检查解码阶段不再依赖采样模型而保留最终合成。保护性停止与 native access violation 分开记录，见 [尝试索引](../../evidence/2026-10-21-repairs/attempts.json)。

## BC-012 · split attention 黑图及奇数长度切片无效 · 数值回归通过，已有大模型独立输出

Kroma 五项 split attention 试验的 latent 全部为 NaN/Inf，虽然原 API success，解码为黑图。相同有限编码条件下，保持模型 FP16，仅增加 `--force-upcast-attention` 后前三项采样归档均有限；删除 FP16 强制参数的另一对照仍由默认选择 FP16，不能误称为 FP32 对照。

双参考换头随后在 attention score 申请 2.19GiB 时 OOM。原切片宽度要求查询长度整除分片数，否则退回整段宽度；奇数序列在反复加倍分片数后仍不缩小分配。[受限预算回归](../../scripts/test_split_attention_precision.py) 直接调用安装的 ComfyUI 实现，修复前失败，改为向上取整后通过且与完整 attention 数值相同。独立 FP16 溢出测试启用升精度通过、禁用失败。

运行时应用的[一行补丁](../../patches/comfyui-uneven-query-split.patch) 与[带备份和 SHA 的应用脚本](../../scripts/apply_split_attention_patch.py) 均在此仓库管理。它修正分片宽度，不代表修好 GGUF native unload，也不代表参考图视觉目标已通过。该 OOM 的清理日志已出现 GGUF `unpatch_model → model.to → GGMLTensor.to` 访问冲突，然后 commit 保护介入；异常栈与最终进程停止方式同时记录。

修正分片及升精度后，Kroma 风格裁切猫头鹰、水彩背向、换头及双参考均得到非黑图输出；风格裁切和背向水彩有独立视觉通过案例，换头和双参考仍部分达到。仅将参考 VAE 降到384是整机 commit 的规避，输出保持512。

## BC-013 · 部分节点校验错误导致有效输出丢失 · 运行器已修复

ComfyUI 可能在返回有效 prompt_id 的同时报告部分输出节点 node_errors；旧重放器立即退出，批次随后停止服务，使已接受的输出丢失。新入口等待 history、保存有效图片与校验错误，返回 partial_output 和非零退出码。[真实 HTTP 行为契约回归](../../scripts/test_replay_partial.py)修复前失败、修复后通过。另在启动前拒绝悬空引用，避免本轮 Turbo 附件两处错误链接再次浪费编码；原错误工作流与失败记录保留。

## BC-014 · Turbo 参考VAE与文本编码同阶段的资源压力 · 四阶段规避实际通过

直接GPU编码在加载阶段触发commit保护；CPU FP16 VAE虽将权重从1288.38MB减为644.19MB，却在进入文本编码前耗时数分钟，被主动停止。两次原失败分别保留，没有当作native crash。

[参考预计算运行器](../../scripts/run_qwen_reference_repair.py)先在独立CPU进程按原TextEncodeQwenImage21处理参考与VAE latent，归档并退出，再在不驻留VAE的GPU文本进程使用相同参考latent。实际参考/GPU文本日志约10.56/35.89秒，完成8步与解码；扩大采样和合成遮罩后，Turbo原例猫变狐目视通过。[过程及真实归档比较](../journal/2026-10-22-repair-journal.md)留有原节点差分测试和全部输入/输出链接。

GPU文本过程中可用物理内存最低观测约94MB，commit最低约2.20GB，因此仍有较高整机压力；本次完整通过不证明长期稳定或native unload根因已修复。新条件复用工具仅在完整依赖与输出槽位一致时复用旧正负条件，初始samples和mask的变化另行逐张量验证。
