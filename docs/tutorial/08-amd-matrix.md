# 08 · AMD 显卡适配矩阵

本仓库不提供 AMD 显卡的兼容性列表。全部结论来自一块 RX 6650 XT（gfx1032），下面只区分“照做已验证”“同架构但没测”“完全没测”，不把未测的卡写成可用或不可用。

## 三档结论

| 档位 | 范围 | 本仓库的记录 |
| --- | --- | --- |
| 已验证 | RX 6650 XT（gfx1032）；Ubuntu 22.04.5 + ROCm 7.14，以及同卡的 Windows 记录 | Ubuntu：安装、GPU 检查、40 项功能（21 通过 / 18 部分达到 / 1 未达到）、连续生成、30 项回归。Windows：95 条原评价与案例；ROCm 7.2 初始化崩溃是未修复的历史问题 |
| 同架构未验证 | RX 6600 / 6600 XT（同为 gfx1032） | 指令集相同、显存同为 8GB，但本仓库没有这两张卡的任何执行记录；不继承 6650 XT 的结论 |
| 未验证 | RDNA1/2/3/4 的其他卡、核显（iGPU）、Instinct | 没有记录；不声称可用，也不声称不可用 |

**本仓库不对未测试的显卡做兼容性承诺。** gfx1032 相同只说明指令集层面接近，不覆盖显存、散热、驱动版本和具体 kernel 选择；“已验证”也只指本机这一套软件组合。

## 先查自己的卡

Linux 下用 ROCm 自带工具确认架构：

```bash
rocminfo | grep gfx
```

再跑仓库的 GPU 最小检查，确认设备名、HIP 版本和小张量计算：

```bash
runtime/ubuntu/.venv/bin/python scripts/check_gpu.py
```

两个结果要一起看：`rocminfo` 能列出设备，不等于 PyTorch 能算。

## HSA_OVERRIDE_GFX_VERSION 的边界

- 它只改变运行时上报的架构，不会补上缺失的 kernel。
- 用错值可能让程序走不匹配的 kernel，把崩溃换成静默的错误结果，比直接失败更难发现。
- 只在明确知道目标架构、并且能逐项检查数值与图像时临时使用，不要写进启动脚本当兼容开关。
- 本仓库的已验证组合没有设置这个变量。

```bash
# 只示意机制；值必须是已知目标架构，不要照抄
export HSA_OVERRIDE_GFX_VERSION="目标架构"
runtime/ubuntu/.venv/bin/python scripts/check_gpu.py
```

ROCm 官方兼容性矩阵按版本列出受支持的卡与系统：[system requirements](https://rocm.docs.amd.com/projects/install-on-linux/en/latest/reference/system-requirements.html)。它回答“驱动和运行时是否支持”，不回答“ComfyUI 与某个模型能否出图”；官方列表没写不等于不能跑，能跑也不等于进入官方支持范围。

## 按显存档位套用

- **8GB**：本仓库的全部证据都在这一档，主力 512–768，靠分阶段与 CPU VAE 控制峰值。边界见 [硬件、系统与版本](./01-hardware.md)。
- **12–16GB**：可以尝试更大分辨率或更多步数，但本仓库没有这些卡的记录。显存更大不会自动解决 GGUF 卸载崩溃、16GB 系统内存峰值和驱动问题。
- **24GB 及以上**：超出本仓库范围。这里的时间、内存和分辨率观察不适用，不要把 8GB 的规避手段当通用配置。
- **任何档位**：先用小图跑通一条最小链路，再跑长任务；一次成功不代表连续运行稳定。

## Windows 上的额外限制

- ROCm on Windows 的支持面比 Linux 窄，公开验证也更少；本仓库 Windows 侧靠 ROCm 7.14 的 multi-arch 轮子出图。
- 更早的 ROCm 7.2 + torch 2.9.1 在 GPU 初始化即原生崩溃，未修复；不能用 7.14 的成功覆盖它。
- 条件允许时优先 Ubuntu：Linux 是唯一从全新独立环境完成全链路验证的路径。这是建议，不是“Windows 不能用”的结论。
- 换系统不改变验证状态：在 Ubuntu 上跑一张未验证的卡，结论仍是未验证。

## 怎么读 21 / 18 / 1

- 40 项功能在 Linux 的结论是 21 通过、18 部分达到、1 未达到；40 项都有输出图片。
- “通过”指该功能至少一条记录达到本例提示目标，不等于每个工作流都能跑，也不等于同进程连续运行稳定。
- 部分达到和未达到保留原图与失败记录；有 PNG 不等于功能通过。
- 这些结论只属于 RX 6650 XT + Ubuntu 22.04.5 + ROCm 7.14，不能外推到同架构卡。

## 把你的卡补进来

贡献实测需要能复核的材料，而不是“我这边可以”的结论：卡型号与 gfx、显存 / RAM、系统 / 内核 / 驱动、ROCm 与 torch 版本、ComfyUI 及插件提交、模型来源与 SHA、输入、提示词、workflow / API、真实输出、耗时（注明是否含冷启动）、失败栈和噪声图。导入成功、实际出图、达到目标、连续稳定是四件事，分开写。

流程与清理要求见 [CONTRIBUTING](../../CONTRIBUTING.md)。

## 相关章节

- [硬件、系统与版本](./01-hardware.md)
- [Windows 环境搭建](./02-windows-setup.md)
- [Ubuntu + ROCm](./03-ubuntu-rocm.md)
- 初始化崩溃、OOM、黑图：[排障](./07-troubleshooting.md)
