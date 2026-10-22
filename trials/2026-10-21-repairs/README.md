# 功能修复实验 · 2026-10-21

这是修复尝试记录，不是全部通过清单。[原始 19 条欠项](../../docs/07-unfinished-features.md) 与失败图片继续保留。`workflows/` 中尚未执行和未目视验收的候选不能算新成果。

## 已完成的实际重试

- **自动反推再出图：通过。** [案例记录](cases/qwen-caption-phased/result.json)、[完整原工作流](cases/qwen-caption-phased/workflow.api.json)、[反推文本](cases/qwen-caption-phased/caption.txt)、[编码与采样绑定](cases/qwen-caption-phased/phase-link.json)。程序从原输入自动生成 caption，再保存条件并由另一个进程出图，无需手填 caption。512×512、15 步；目视为正常雨夜橘猫与暖色橱窗。两阶段提交后检测到成功约 103 与 154 秒，不含服务冷启动。文本与上一轮有 caption 无图片的失败尝试逐字节相同。见 [资源测量及限制](cases/qwen-caption-phased/measurements.json)：编码阶段仍有较高 RAM 峰值，不能描述成整个流程只占 2GB。
- **中文替换茶壶：通过。** [结果与图片](cases/flux2-teapot-structure/result.json)。明确单壶嘴、右侧把手的中文描述后，目视结构正常，保留灰色产品摄影背景。这是本案例的提示词改进，不是模型结构通用补丁。
- **水彩保持夜景：通过。** [结果与图片](cases/flux2-watercolor-night/result.json)。深蓝夜色、人工灯光、背向猫和水彩纸纹保留；细节仍有风格重画。
- **原生 1024²：运行通过，完整指令部分达到。** [结果与图片](cases/flux2-1024-attention/result.json)。完整四步采样、CPU 解码和保存，HELLO 清楚。仍有额外招牌文字，未满足 `no other writing`；单次成功也不能证明旧 native Aborted 根因已修复。当前批次保留默认 pinned，增加 split attention，不能将改变注意力实现直接当作确定根因。
- **小蝴蝶结：仍部分达到。** [未达尺寸的结果](cases/flux2-tiny-bow/result.json)。蓝包保留，但含飘带的整体仍明显大于提示词要求。继续保留欠项。
- **Qwen 遮罩内猫到狐狸：通过。** [输出及输入/遮罩](cases/qwen-mask-fox-reference/result.json)。先抹去原猫的参考条件，再加入狐狸参考，产出长吻、黑耳黑腿和白尾尖的明确狐狸；头部略向右转。最终合成之外 193,144 像素无变化，保留由合成实现。
- **Qwen 多参考合成：部分达到。** [独立重试](cases/qwen-multiref-local-composite/result.json)。明确狐狸、背景在遮罩之外保持；眼部身份不同且尾部被右边界截断，不能认定精确主体迁移。
- **Qwen 换头/仅换脸：部分达到。** [普通换头](cases/qwen-head-direction-mask/result.json)、[仅面部](cases/qwen-face-only-mask/result.json)。侧脸方向、服装和发型目标有所改善，但身份特征与参考仍有差异；普通换头右侧还有黑发残留。
- **BFS 三阶段：运行完成，视觉部分达到。** [独立结果](cases/qwen-bfs-direction-mask/result.json)。编码、15 步 FP16 采样、CPU 解码各自退出后再启动下一阶段。避开先前完成采样后加载 VAE 时的 commit 保护停止；仍有黑发残留和身份差异，不当作 BFS 精确身份复现通过。
- **Kroma 风格参考新主体：通过一个裁切参考配方。** [无狐狸参考区域的猫头鹰](cases/kroma-style-no-subject-reference/result.json)。同一参考只裁取森林/蓝橙配色区域再编码，输出猫头鹰且没有狐狸，纸纹与配色保留。[完整参考的对照](cases/kroma-style-owl-explicit/result.json) 仍多出狐狸，不能当作通过。
- **Kroma 水彩姿态与换头：仍部分达到。** [低 denoise 水彩](cases/kroma-watercolor-denoise040/result.json) 仍把背向猫变成可见面部的侧脸；[换头](cases/kroma-head-direction-mask/result.json) 有黑发和颈部叠影，不能作为可用成品验收。正常出图只是执行通过。
- **Z-Image CPU 文本编码：单次完整通过。** [红壶与两颗柠檬](cases/zimage-cpu-text-fp16/result.json)。明确 CPU FP16 文本编码、9 步、512²、CPU VAE，提交到 history 约 192.5 秒；没有用 GPU 文本配置替代。见 [RAM/commit 观测](cases/zimage-cpu-text-fp16/measurements.json)：峰值进程树 RSS 约 8.26GB，可用物理内存最低约 491MB，commit 余量最低约 1.40GB，仍有较高整机压力；精确峰值显存未采样。单次成功不证明旧连续崩溃根因解决。

![自动反推后生成的独立图片](cases/qwen-caption-phased/7-0-qwen-caption-gpu-chunked_00001_.png)

![结构正常的中文替换茶壶](cases/flux2-teapot-structure/19-0-flux2-teapot-structure_00001_.png)

![仍保留夜景的水彩重试](cases/flux2-watercolor-night/19-0-flux2-watercolor-night_00001_.png)

## Qwen 反推内存

原 CPU 失败申请 2,489,319,424 字节，对应 INT8 `lm_head` 的 `151936 × 4096 × float32` 全词表反量化临时矩阵。新 [可选插件](../../code_source/cpu_chunked_logits/bounded.py) 每次最多处理 2048 行；4096 隐藏维的 float32 临时权重块约 32MiB。它只处理指定 INT8 布局与明确的浮点回退条件，不改权重，也不承诺整个 8B 模型只占 32MiB。

回归调用真实 `BaseQwen3.logits`、MixedPrecisionOps Linear 和 ConvRot INT8 布局：未修版本触发全词表内存预算异常；新版本与直接完整 Linear 的数值比较须通过。测试不是在 2.49GB 实际分配处制造系统 OOM，而是在同一真实调用路径检查反量化块大小。

已有大模型实测：

- CPU 分块路径已产生首 token，但约 389 秒才开始，两 token 后人工停止，完整任务未通过。
- GPU 分块路径生成了与雨夜橘猫输入相符的完整英文反推文字，见 [原文与下游绑定](caption-stage-link.json)。随后在量化文本编码器 GPU→CPU 卸载时 `0xC0000005`，没有图片；不能把有 caption 当作功能通过。
- 把该 caption 原样交给独立 CPU 编码出图任务，后续采样先报显存不足，清理阶段原生退出，仍没有图片。
- 分阶段编码初试在整机可用内存约 0.5GB 时人工停止。进程被停止的退出码不能当作自然崩溃。

## 分阶段规避实验

[条件归档节点](../../code_source/repair_conditioning/__init__.py) 将正/负条件、参考 latent、采样 latent 与遮罩按原 dtype 和数值保存。编码进程退出后，采样进程读取带 SHA-256 校验的条件；不需要再次加载文本编码器。这样测试能否避开模型切换期间的原生卸载崩溃。它是进程隔离规避，不是底层 HIP/量化卸载补丁。

归档只允许密集张量、字典、列表、元组和基础值；不支持的元数据明确报错。测试覆盖共享存储、非连续张量、嵌套 metadata、精确往返、文件校验与目录边界。图裁剪测试确认采样参数、模型和最终局部合成依赖保留，编码依赖才被移除。

辅助节点复制到本地 `ComfyUI/custom_nodes/`。后续奇数长度 attention 排查另增加一行核心修正，见下文的补丁与前后回归；原始文件备份、日志、条件张量和模型文件留在本地，不纳入仓库。

```powershell
python scripts/run_conditioned_repair.py --runtime D:\MyProject\amd_comfy `
  --workflow trials/2026-10-21-repairs/workflows/qwen-caption-gpu-chunked.api.json `
  --gpu-chunked-logits --out runs/caption-new-attempt
```

`--encode-extra-arg=--disable-pinned-memory` 仅用于单独的文本编码实验；不能据此关闭 FLUX.2 采样的锁页内存。模型缓存 YAML 可通过 `--model-paths` 传入，实际命令保存在每次运行目录。完整图片及目视结论仍是验收条件。

多份独立工作流可一起传入 `--workflow`：先逐项编码，确认编码进程已退出，再逐项采样；每项拥有自己的条件 SHA、实际 API、history 与输出。批次在错误处停止，未执行的后续项不会记为通过。运行器也记录 Windows commit 余量，低于该次记录的保护阈值时主动停止自己的测试进程；这是保护性停止，不能登记成自然崩溃。

## 内存隔离与失败证据

标准运行器 [尝试索引](attempts.json) 保留本地原始日志的 SHA、执行状态与保护停止；早期单独反推尝试另见上文的阶段绑定。没有把失败从清单删掉。Qwen 两参考编码使用原生动态显存后，五项编码完成；旧 legacy 编码先触发 commit 保护。文本条件与 latent 均按原值归档，不需要改为手写 caption。

`--cache-none` 仍在同一服务的第二项触发保护，不能当作跨案例内存保留的修复。`--isolate-sampling` 每项重建进程，`--isolate-decode` 还把采样 latent 写成带 SHA 的归档，退出 GPU 进程后用 `--cpu` 解码；后者保留完整最终合成与输入/遮罩输出。这些是资源受限机器上的流程规避，底层原生卸载问题没有因此结案。

早期保护阈值为 512MiB；后续整机 commit 紧张时将新启动任务的默认阈值提高到 1024MiB。`summary.json` 新增实际阈值、最终进程退出码及日志中是否观察到原生异常/OOM，避免把保护停止当成对更早异常的否定。历史阈值与结果不被重写。

可选 `--python-executable` 指向已存在的解释器。本轮将已有环境复制到 G 盘后校验关键文件并最小初始化 GPU，没有更换 torch 或下载另一套模型。模型缓存同样仅复制原权重，保持 SHA 相同。原始环境保留。

## Kroma 黑图对照

初次 split attention 批次五项均返回 success，但每份采样 latent 的 65,536 个 F32 元素全部为非有限值，解码有 `invalid value encountered in cast`。见 [五份独立归档检查](attempts/kroma-fp16-nonfinite/latent-check.json) 与 [首项黑图和实际 API](attempts/kroma-fp16-kroma-style-owl-explicit/result.json)；其余失败图片也各自保留在 `attempts/`，不替换为后来正常图片。

删除 `--fp16-unet` 的对照仍由本机默认选择 FP16，并被新增归档检查拦截；名为 `kroma-repairs-f32-v2` 的本地目录不是实际 FP32 实验，必须以日志的 dtype 为准。相同编码条件均为有限值，检查结果另存本地。后续只增加 `--force-upcast-attention` 比较 attention 分数精度，已有独立 PNG 与逐项目视结论；黑图、正常出图和视觉通过仍分别记录。

归档写入和读取现在均拒绝 NaN/Inf。额外的 [split attention 数值回归](../../scripts/test_split_attention_precision.py) 调用已安装 ComfyUI 的真实实现，用有限 FP16 Q/K 检查 score 溢出与升精度后的正确均值；这是数值机制检查，不能替代本机大模型与图片验收。Kroma 的显式 `--sampling-profile kroma` 选择 split attention 加升精度，其余模型的默认设置不变。

双参考换头在升精度后还触发 2.19GiB attention 分配失败。旧公式在查询长度不能整除分片数时退回整段长度，增加分片仍不能减少分配。[一行补丁](../../patches/comfyui-uneven-query-split.patch) 改为向上取整的分片宽度，允许末片较短。实际调用原实现的 5-query 受限预算回归先失败，应用补丁后与完整 attention 数值一致；另一个 FP16 溢出回归启用升精度通过、关闭升精度失败。见 [补丁 SHA 与退出状态](patches/split-attention.json)。

应用命令：`python scripts/apply_split_attention_patch.py --runtime <本地运行根目录> --record runs/runtime-patches/split-attention.json`。脚本识别唯一旧语句、编译检查、保存原文件和前后 SHA；未知源码拒绝修改，重复运行保留原补丁记录。当前基于 ComfyUI `ce1e922d8623bb507180e32a0c01a7d0e29edef7` 实测。OOM 清理中同时观察到 GGUF 卸载访问冲突，随后保护停止介入；日志异常与最终保护停止分别保留，不把它简化成只有人工中止。


## 2026-10-22 补充验收

- [Kroma 背向水彩](cases/kroma-watercolor-back-view/result.json)：水彩纸面、雨夜光照、严格背向猫均目视通过。低 denoise 的失败对照仍保留。
- [Turbo 换头](cases/turbo-head-direction-mask/result.json)与 [BFS 扩大遮罩](cases/qwen-bfs-full-hair-tiled/result.json)：旧黑发残留消除，侧转及服装保留；五官身份仍有差异，继续登记部分达到。BFS 复用相同采样 latent，只扩大最终合成遮罩并进行 tiled CPU VAE 解码，不能冒称新一次采样。
- [Kroma 384 参考](cases/kroma-multiref-ref384/result.json)：仅两路参考 VAE 分辨率降低，输出仍 512；运行完整，苔石污染与主体重影仍未通过。
- [MOSS FP16](cases/moss-watercolor-denoise085/result.json)：显式半精度使八步正常完成，水彩效果仍不足。原 BF16/manual F32 加载后的保护停止保留。
- [第二次蝴蝶结](cases/flux2-tiny-bow-fingertip/result.json)：红结宽 48px，包体宽 259px，比例约18.5%，仍未满足指甲大小。
- [Turbo 狐狸恢复](cases/turbo-mask-fox-reference/result.json)：修正本次附件图中两处无效节点引用，校验原编码与采样语义和归档 SHA 后复用采样，只重新解码。背向轮廓仍偏猫，不能把有图认定物种替换成功。错误原图保留在 attempts/turbo-fox-invalid-attachments/。

### 工具与数值防回归

[前置工作流检查](../../scripts/workflow_checks.py)在启动模型前拒绝悬空节点引用；[部分输出回归](../../scripts/test_replay_partial.py)模拟同次提交中一个输出无效、另一个被 ComfyUI 接受的真实 HTTP 行为。运行器现在等有效任务结束，保留 history/PNG 和 validation_errors，返回 partial_output 及非零退出码，避免丢图或误报全通过。

[条件归档测试](../../scripts/test_repair_conditioning.py)覆盖6项，包括在写入和读取时拒绝 NaN/Inf；无效 latent 不再静默变成黑色 PNG。CPU 编码、CustomAdvanced/CFGGuider、采样复用和解码后处理各自保留实际 API。仅 provenance digest 改变允许复用，seed/模型/数值参数改变仍拒绝。

- [Kroma 去干扰参考](cases/kroma-multiref-clean-reference/result.json)：苔石与原猫重影消失，但灰色参考底板也被迁入画面；仍部分达到，不能作为融合通过。

- [MOSS 原生 SFT 水彩](cases/moss-watercolor-base-sft/result.json)：移除八步 DMD LoRA，28步、CFG3、denoise0.85、显式 FP16 后，纸纹、大笔触、丛林和全身宇航员目视通过。此为不同配方的独立重试；不改写八步未达风格的记录。

[本轮回归汇总](verification.json)：修复路径22项测试通过；另单独运行未启用分块的原调用，按预期触发词表反量化预算异常。attention 的原实现失败/修正后通过证据见补丁记录。

- [固定尺寸小蝴蝶结合成](cases/flux2-tiny-bow-sized-composite/result.json)：22×20 局部贴片、原蓝包背带底部。目视尺寸通过，遮罩外像素变化为0。上游模型图及哈希见 [上游绑定](cases/flux2-tiny-bow-sized-composite/upstream.json)。这是后处理规避，直接 FLUX 尺寸遵循仍未通过；首轮遮罩附件高度误写688的记录保留，最终使用实际672。

本轮最终报告核对：75条结果记录，图片绑定/元数据错误0、报告缺图0。该数字包含历史失败、素材、诊断及独立重试，不是75项功能全部通过。原8188服务在串行测试结束后恢复。
