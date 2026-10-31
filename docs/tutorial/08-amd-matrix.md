# 08 · 你的卡不是 RX 6650 XT：怎么套用

我没有 AMD 显卡的兼容性列表。所有结论都来自一块 RX 6650 XT（gfx1032）。下面只分三档：照做已验证的、同架构但没测过的、完全没测过的。没测过的卡，我不写成可用，也不写成不可用。

## 三档结论

| 档位 | 范围 | 记录 |
| --- | --- | --- |
| 已验证 | RX 6650 XT（gfx1032）；Ubuntu 22.04.5 + ROCm 7.14，以及同卡的 Windows 记录 | Ubuntu：安装、GPU 检查、40 项功能（21 通过 / 18 部分达到 / 1 未达到）、连续生成、30 项回归。Windows：95 条原评价与案例；ROCm 7.2 初始化崩溃是未修复的历史问题 |
| 同架构未验证 | RX 6600 / 6600 XT（同为 gfx1032） | 指令集相同、显存同为 8GB，但这两张卡没有任何执行记录；不继承 6650 XT 的结论 |
| 未验证 | RDNA1/2/3/4 的其他卡、核显（iGPU）、Instinct | 没有记录；不声称可用，也不声称不可用 |

没测过的显卡，我不做兼容承诺。gfx1032 相同只说明指令集层面接近，显存、散热、驱动版本和具体 kernel 选择都不在这个范围内。「已验证」也只指这台机器上这一套软件组合。

## 先查自己的卡

Linux 下用 ROCm 自带的工具确认架构：

```bash
rocminfo | grep gfx
```

再跑仓库的 GPU 最小检查，确认设备名、HIP 版本和小张量计算：

```bash
runtime/ubuntu/.venv/bin/python scripts/check_gpu.py
```

两个结果要一起看。`rocminfo` 能列出设备，不等于 PyTorch 能算。

## HSA_OVERRIDE_GFX_VERSION 能做什么，不能做什么

- 它只改变运行时上报的架构，缺的 kernel 不会因此补上。
- 值用错了，程序可能走到不匹配的 kernel 上，把崩溃换成静默的错误结果，比直接失败更难发现。
- 只在明确知道目标架构、并且能逐项检查数值和图像时临时用一下。别写进启动脚本当兼容开关。
- 这套配置没有设置这个变量。

```bash
# 只示意机制；值必须是已知目标架构，不要照抄
export HSA_OVERRIDE_GFX_VERSION="目标架构"
runtime/ubuntu/.venv/bin/python scripts/check_gpu.py
```

ROCm 官方的兼容性矩阵按版本列出受支持的卡和系统，见 [system requirements](https://rocm.docs.amd.com/projects/install-on-linux/en/latest/reference/system-requirements.html)。它回答的是「驱动和运行时支不支持」，不回答「ComfyUI 配某个模型能不能出图」。官方列表没写不等于不能跑，能跑也不等于进了官方支持范围。

## 按显存档位对号入座

- 8GB：全部证据都在这一档，主力 512 到 768，靠分阶段和 CPU VAE 控制峰值。边界见 [硬件、系统与版本](./01-hardware.md)。
- 12GB 到 16GB：可以试更大的分辨率或更多步数，但这些卡没有任何记录。显存更大不会自动解决 GGUF 卸载崩溃、16GB 系统内存峰值和驱动问题。
- 24GB 及以上：超出这份记录的范围。这里的时间、内存和分辨率观察都不适用，别把 8GB 的规避手段当通用配置。
- 任何档位：先用小图跑通一条最小链路，再跑长任务。一次成功不代表连续运行稳定。

## Windows 上还多一层限制

- ROCm on Windows 的支持面比 Linux 窄，公开验证也少。这套记录在 Windows 侧是靠 ROCm 7.14 的 multi-arch 轮子出图的。
- 更早的 ROCm 7.2 + torch 2.9.1 在 GPU 初始化就原生崩溃，没修。不能用 7.14 的成功盖过它。
- 条件允许就优先 Ubuntu，Linux 是唯一从全新独立环境走完全链路验证的路径。这是建议，不是「Windows 不能用」的结论。
- 换系统不改变验证状态。在 Ubuntu 上跑一张没验证过的卡，结论还是未验证。

## 怎么读 21 / 18 / 1

- 40 项功能在 Linux 的结论是 21 项通过、18 项部分达到、1 项未达到，40 项都有输出图片。
- 「通过」指该功能至少有一条记录达到了本例的提示目标。它不等于每个工作流都能跑，也不等于同进程连续运行稳定。
- 部分达到和未达到的条目保留了原图和失败记录。有 PNG 不等于功能通过。
- 这些结论只属于 RX 6650 XT + Ubuntu 22.04.5 + ROCm 7.14，不能外推到同架构的卡。

## 把你的卡补进来

想贡献一份实测，得拿出别人能复核的材料。「我这边可以」这句话本身没用。需要写清楚：卡型号与 gfx、显存和内存、系统 / 内核 / 驱动、ROCm 与 torch 版本、ComfyUI 及插件提交、模型来源与 SHA、输入、提示词、workflow / API、真实输出、耗时（注明是否含冷启动）、失败栈和噪声图。

导入成功、实际出图、达到目标、连续稳定是四件事，分开写。流程和清理要求见 [CONTRIBUTING](../../CONTRIBUTING.md)。

## 证据与出处

分档依据、各项功能的判定和平台计数在 [功能报告](../../report/feature-report.md) 与 [故障追踪与根因边界](../reference/failure-tracker.md)。ROCm 官方的支持范围以 [system requirements](https://rocm.docs.amd.com/projects/install-on-linux/en/latest/reference/system-requirements.html) 为准。

## 怎么确认这一步成功了

1. `rocminfo | grep gfx` 打印出你的 gfx 编号，你知道它在三档里属于哪一档。
2. `check_gpu.py` 能跑通，设备名和 HIP 版本都打印出来了。
3. 你没有设置 `HSA_OVERRIDE_GFX_VERSION`，或者设置了但能说清目标架构和验收方法。
4. 你先用小图跑通了一条最小链路，用的参数和已验证的那套配置一致。

## 卡住了看哪里

- 不知道自己算哪一档：先看 [01 章](./01-hardware.md) 的配置表，再回来对档位。
- Linux 装不上：回 [Ubuntu + ROCm](./03-ubuntu-rocm.md)。
- Windows 装不上：回 [Windows 环境搭建](./02-windows-setup.md)。
- 初始化崩溃、OOM、黑图：[排障](./07-troubleshooting.md)。
