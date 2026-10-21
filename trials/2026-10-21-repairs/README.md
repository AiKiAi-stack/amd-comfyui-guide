# 功能修复实验 · 2026-10-21

这是修复尝试记录，不是全部通过清单。[原始 19 条欠项](../../docs/07-unfinished-features.md) 与失败图片继续保留。`workflows/` 中尚未执行和未目视验收的候选不能算新成果。

## 已完成的实际重试

- **自动反推再出图：通过。** [案例记录](cases/qwen-caption-phased/result.json)、[完整原工作流](cases/qwen-caption-phased/workflow.api.json)、[反推文本](cases/qwen-caption-phased/caption.txt)、[编码与采样绑定](cases/qwen-caption-phased/phase-link.json)。程序从原输入自动生成 caption，再保存条件并由另一个进程出图，无需手填 caption。512×512、15 步；目视为正常雨夜橘猫与暖色橱窗。两阶段提交后检测到成功约 103 与 154 秒，不含服务冷启动。文本与上一轮有 caption 无图片的失败尝试逐字节相同。见 [资源测量及限制](cases/qwen-caption-phased/measurements.json)：编码阶段仍有较高 RAM 峰值，不能描述成整个流程只占 2GB。
- **中文替换茶壶：通过。** [结果与图片](cases/flux2-teapot-structure/result.json)。明确单壶嘴、右侧把手的中文描述后，目视结构正常，保留灰色产品摄影背景。这是本案例的提示词改进，不是模型结构通用补丁。
- **水彩保持夜景：通过。** [结果与图片](cases/flux2-watercolor-night/result.json)。深蓝夜色、人工灯光、背向猫和水彩纸纹保留；细节仍有风格重画。
- **原生 1024²：运行通过，完整指令部分达到。** [结果与图片](cases/flux2-1024-attention/result.json)。完整四步采样、CPU 解码和保存，HELLO 清楚。仍有额外招牌文字，未满足 `no other writing`；单次成功也不能证明旧 native Aborted 根因已修复。当前批次保留默认 pinned，增加 split attention，不能将改变注意力实现直接当作确定根因。
- **小蝴蝶结：仍部分达到。** [未达尺寸的结果](cases/flux2-tiny-bow/result.json)。蓝包保留，但含飘带的整体仍明显大于提示词要求。继续保留欠项。

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

仅复制两个辅助节点目录到本地 `ComfyUI/custom_nodes/`，没有修改 ComfyUI 核心源码。原始日志、条件张量和模型文件只保存在本地，不纳入仓库。

```powershell
python scripts/run_conditioned_repair.py --runtime D:\MyProject\amd_comfy `
  --workflow trials/2026-10-21-repairs/workflows/qwen-caption-gpu-chunked.api.json `
  --gpu-chunked-logits --out runs/caption-new-attempt
```

`--encode-extra-arg=--disable-pinned-memory` 仅用于单独的文本编码实验；不能据此关闭 FLUX.2 采样的锁页内存。模型缓存 YAML 可通过 `--model-paths` 传入，实际命令保存在每次运行目录。完整图片及目视结论仍是验收条件。

多份独立工作流可一起传入 `--workflow`：先逐项编码，确认编码进程已退出，再逐项采样；每项拥有自己的条件 SHA、实际 API、history 与输出。批次在错误处停止，未执行的后续项不会记为通过。运行器也记录 Windows commit 余量，低于默认 512MiB 时主动停止自己的测试进程；这是保护性停止，不能登记成自然崩溃。
