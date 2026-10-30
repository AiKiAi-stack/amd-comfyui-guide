# 07 · 遇到的坑（排障）

## torch 初始化就原生崩溃

独立 ROCm 7.2 + torch 2.9.1 在 `torch.cuda.is_available()` 出现 Windows access violation。先运行 `scripts/check_gpu.py`；最小张量没过就不要继续加载模型。当前成功图来自另一套 ROCm 7.14 环境，不能把它当作 7.2 已修好。

## MOSS：HIPBLAS_STATUS_INVALID_VALUE

首轮在 0/50 的 INT8 QKV 层失败，伴随 gfx1032 kernel 缺失。`code_source/gfx1032_quant_fallback` 使用 ComfyUI 原有反量化后浮点计算路径，只有显式开关才生效。不是替换权重，也不是补齐原生 INT8 kernel；会改变该进程内相关计算能力选择。

## MOSS：API success 但全是纹理噪声

错误使用 `ModelSamplingSD3` 把 timestep multiplier 改成 1000；换 `ModelSamplingAuraFlow`，保持 multiplier 1、shift 5 后出图。旧噪声图和 history 保留。成功返回不等于采样配置正确。

## GGUF：第二次加载/卸载时 0xC0000005

Qwen、Z-Image 的 `GGMLTensor.to` / `partially_unload` 路径出现过原生异常。关闭异步卸载只规避部分情况；Qwen prefix cache 关闭后多参考成功；Turbo-UN 还采用 CPU 文字/视觉编码和 CPU VAE。独立进程隔离失败有帮助，不能称根因修复。`fast-disk` 开关不等于关闭 GGUF 自身 mmap。

## Kroma：看似 512，参考节点内部仍升到 1024

原参考路径 softmax OOM 并 Aborted。改用独立 `VAEEncode + ReferenceLatent` 的512参考后出图，但语义功能仍需目视验收。不能把降尺寸后的图登记成原1024任务成功。

## FLUX.2：--disable-pinned-memory 导致噪声

本机两个 API-success 结果是噪声。新服务移除该参数、恢复默认锁页内存后，文生图与七项编辑成功。这只是特定本机组合的对照，底层 HIP/WDDM 根因尚未确定。Z-Image 某配置能工作也不能外推 FLUX 正常。

## SSD、CPU 编码与“8GB能跑”的含义

本机 D: 为 SATA HDD，G: 为 NVMe；后续成功案例使用 G: 模型副本，且也改变了文字编码与动态显存配置。不能把速度变化全部归因于 SSD。8GB文件不是8GB运行显存；16GB系统内存也可能成为瓶颈，CPU编码不一定更实用。

