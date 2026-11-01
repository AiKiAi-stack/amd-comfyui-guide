# 实测环境

教程正文按「8 GB 一档的 AMD 卡」来写，不把某一张卡当成读者范围。所有数字来自同一台机器，完整配置集中放在这里，需要核对时再翻。

## 配置

| 项目 | Windows | Ubuntu（从零走完全程） |
| --- | --- | --- |
| 显卡 | AMD Radeon RX 6650 XT（gfx1032） | 同左 |
| 显存 | 8 GB（ComfyUI 报告 8,176 MB） | 8 GB（8,573,157,376 字节） |
| 内存 | 16 GB（16,197 MB） | 16 GB，无 swap |
| 系统 / 内核 | Windows 10.0.19045 | Ubuntu 22.04.5 / 6.8.0-138-generic |
| 显卡驱动 | AMD 32.0.21045.5002 | amdgpu（随内核） |
| Python | 3.12.6 | 3.12.14（系统 3.10 未替换） |
| ROCm / HIP | 7.14.0 | 7.14.0 / 7.14.60850 |
| torch | 2.12.0+rocm7.14.0 | 2.12.0+rocm7.14.0 |
| ComfyUI | ce1e922d8623bb507180e32a0c01a7d0e29edef7 | 同左 |
| ComfyUI-GGUF | 373048b8403a7820620065210a691263d4da0a61 | 同左 |

torchvision 两个平台都是 0.27.0+rocm7.14.0。torchaudio 2.11.0+rocm7.14.0 只有 Windows 装了，Linux 没装。

Windows 这一列是按已验证环境的版本快照整理的复现路径，没有在全新 Windows 上完整重跑一遍；Ubuntu 那一列是从全新独立环境走完的。

系统名有一处出入。`machine.json` 记的是 `Microsoft Windows 10 家庭版`、版本 10.0.19045，而 Windows 章节按 Windows 11 的界面来写。系统版本没有另外核过，对照时以 10.0.19045 这个版本号为准。

## 平台覆盖

两个平台合计 162 条记录，Windows 95 条，Linux 67 条。这两个数字只说明覆盖范围，不说明哪个平台更好。

Windows 那 95 条包括原评价与案例、GPU 检查、分阶段规避和 768 基线。能看的成功图来自 ROCm 7.14 环境。更早那套独立的 ROCm 7.2 + torch 2.9.1 在 `torch.cuda.is_available()` 就出 access violation，至今没修，两套不能混着说。那台机器上还留着早期 ROCm 7.2 包的安装元数据，不代表旧栈能用。

Ubuntu 22.04.5 + ROCm 7.14 是唯一从全新独立环境走完「安装 → GPU 检查 → 出图 → 连续生成 → 回归」的路径：Linux 40 项功能里 21 项通过、18 项部分达到、1 项没达到。

两个平台的提示词、编码器、精度和进程方式都不一样，耗时不能横向排名。

## 证据出处

配置数值和记录在 [machine.json](../../environment/machine.json)、[Windows 安装来源](../../environment/install-provenance.md)、[Windows 包快照](../../environment/packages.json)、[Ubuntu 环境记录](../../environment/ubuntu-2026-10-23/)、[GPU 计算检查](../../environment/ubuntu-2026-10-23/gpu-compute.json) 和 [Ubuntu 部署日志](../journal/2026-10-23-ubuntu-setup.md) 里。
