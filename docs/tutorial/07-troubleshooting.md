# 07 · 遇到的坑

这一章按症状排。先找到和你看到的一样的那一段，再去动配置。

## torch 一初始化就原生崩溃

独立装 ROCm 7.2 + torch 2.9.1 时，`torch.cuda.is_available()` 直接 Windows access violation。

先跑 `scripts/check_gpu.py`，最小的张量运算都过不了，就别继续加载模型。现在这些成功图来自另一套 ROCm 7.14 环境，别当成 7.2 已经修好了。

## MOSS：HIPBLAS_STATUS_INVALID_VALUE

第一轮在 0/50 的 INT8 QKV 层就失败，报错里带着 gfx1032 kernel 缺失。

用 `code_source/gfx1032_quant_fallback`。它走 ComfyUI 原有的反量化加浮点计算路径，只有你显式打开开关才生效。它没有替换权重，也没有补齐原生的 INT8 kernel，只是改变了这个进程里相关计算能力的选择。

## MOSS：API 成功了，图却全是纹理噪声

原因是 `ModelSamplingSD3` 被错误地设成 timestep multiplier 1000。换成 `ModelSamplingAuraFlow`，保持 multiplier 1、shift 5，图就出来了。

旧的噪声图和 history 都留着。成功返回不等于采样配置对。

## GGUF：第二次加载或卸载时 0xC0000005

Qwen 和 Z-Image 的 `GGMLTensor.to`、`partially_unload` 路径上都出现过原生异常。

关掉异步卸载只能规避一部分情况。Qwen 关掉 prefix cache 之后多参考成功了；Turbo-UN 还额外用了 CPU 文字编码、视觉编码和 CPU VAE。独立进程隔离确实有帮助，但这不能算根因修好。另外 `fast-disk` 开关不等于关掉 GGUF 自己的 mmap。

## Kroma：看着是 512，参考节点内部还是升到 1024

原参考路径 softmax OOM，进程 Aborted。

改成独立的 `VAEEncode + ReferenceLatent`、512 参考之后能出图，但语义功能仍然要目视验收。降尺寸之后的图，别登记成原来那个 1024 任务的成功。

## FLUX.2：`--disable-pinned-memory` 会导致噪声

我这台机器上，两个「API 成功」的结果都是噪声图。

新服务去掉这个参数、恢复默认锁页内存之后，文生图和七项编辑都成功。这只是这一套本机组合的对照，底层的 HIP/WDDM 根因还没定。Z-Image 某个配置能工作，也不能外推成 FLUX 正常。

## SSD、CPU 编码和「8GB 能跑」

本机 D: 是 SATA HDD，G: 是 NVMe。后面成功的案例用了 G: 上的模型副本，同时也改了文字编码和动态显存配置。所以速度变化不能全记在 SSD 头上。

8GB 的文件不是 8GB 的运行显存。16GB 系统内存也可能先成为瓶颈，CPU 编码也不一定更实用。

## 怎么确认这一步成功了

修完之后，按这四条验收：

1. 同一个输入重跑一次，问题不再出现，而且命令和参数和失败时是同一套。
2. 你记下了改的是哪一个参数或哪一个文件，而不是「重启了一下就好了」。
3. 出新图了，且你已经看过这张图，不是只看 API 返回成功。
4. 失败的图和 history 还在，没有覆盖旧记录。

## 卡住了看哪里

- 崩溃或 OOM 的具体编号和「已确认 / 未确认」划分：[故障追踪与根因边界](../reference/failure-tracker.md)。
- 显卡不在已验证的档位：[AMD 卡适配矩阵](./08-amd-matrix.md)。
- 不知道该先改哪个参数：回 [03 章](./03-ubuntu-rocm.md) 的「这套环境目前能跑到哪」，对照自己的现象。
- 换系统之后问题还在：看 [08 章](./08-amd-matrix.md) 的「Windows 上的额外限制」，换系统不会改变验证状态。
