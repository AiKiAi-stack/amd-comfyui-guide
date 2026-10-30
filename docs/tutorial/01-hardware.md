# 01 · 硬件、系统与版本

本仓库的结论只来自一台机器、一张显卡。本章固定这套实测组合，说明 8GB 显存在现有证据里的实际含义，以及哪些问题本指南回答不了。

## 已验证组合

| 项目 | Windows | Ubuntu（完整验证路径） |
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

Windows 侧另有 torchaudio 2.11.0+rocm7.14.0，Linux 未安装。两平台 torchvision 均为 0.27.0+rocm7.14.0。来源：[machine.json](../../environment/machine.json)、[Windows 安装来源](../../environment/install-provenance.md)、[Windows 包快照](../../environment/packages.json)、[Ubuntu 环境记录](../../environment/ubuntu-2026-10-23/)、[GPU 计算检查](../../environment/ubuntu-2026-10-23/gpu-compute.json)、[Ubuntu 部署日志](../journal/2026-10-23-ubuntu-setup.md)。

`machine.json` 记录的系统名是 `Microsoft Windows 10 家庭版`、版本 10.0.19045；教程其他位置按 Windows 11 叙述。本表按元数据写，系统版本未单独核验。

装好后先核对提交，和上表不一致时不要直接套用本文结论：

```bash
# 在 ComfyUI 源码目录执行
git rev-parse HEAD
git -C custom_nodes/ComfyUI-GGUF rev-parse HEAD
```

## 8GB 显存在这里意味着什么

- 主力尺寸是 512×512。768 只出现在早期基线和个别 Windows 记录，例如 Qwen Base 的 768 文生图、旧 768² 16 步基线，不是默认值。
- 分阶段隔离是常规手段：文本编码、采样、CPU 解码拆成独立进程，条件与 latent 通过归档传递，见 [三阶段运行器](../../scripts/run_conditioned_repair.py) 与 [Qwen 参考阶段](../../scripts/run_qwen_reference_repair.py)。
- CPU VAE 默认开启（[start_ubuntu.sh](../../scripts/start_ubuntu.sh) 的 `--cpu-vae`），用时间换显存。
- 1024 只在个案里成立：FLUX 1024 在采样完成后、CPU 解码时触发内存保护，改 tile 256 / overlap 64 分块解码才得到图片；Kroma 参考链内部升到 1024 时 OOM。不能据此说“8GB 能跑 1024”。
- 长任务同样按个案看：Z-Image 同进程连续三张通过；Qwen pinned 首次完整加载十多分钟未完成、人工停止。一次成功不升级为长期稳定。

## Windows 与 Ubuntu 各自被记录的范围

两平台合计 162 条记录（95 Windows / 67 Linux）。

- Windows 侧有 95 条原评价与案例、GPU 检查、分阶段规避和 768 基线；当前成功图来自 ROCm 7.14 环境。更早的独立 ROCm 7.2 + torch 2.9.1 环境在 `torch.cuda.is_available()` 即发生 access violation，是未修复的历史问题，两者不能混用。本机仍留有早期 ROCm 7.2 包的安装元数据，它不证明旧栈可用。
- Ubuntu 22.04.5 + ROCm 7.14 是唯一从全新独立环境走完“安装 → GPU 检查 → 出图 → 连续生成 → 回归”的路径：Linux 40 项功能 21 通过、18 部分达到、1 未达到。
- 这不等于 Windows 不可用，也不等于 Ubuntu 换一台机器必然成功。两平台的提示词、编码器、精度和进程方式不同，耗时不能当系统性能排名。

## 本指南不覆盖什么

- 其他显卡：只在 [AMD 显卡适配矩阵](./08-amd-matrix.md) 给出“已验证 / 同架构未验证 / 未验证”三档，不对未测卡做兼容承诺。
- 其他模型权重：只测 7 个模型系列、40 项功能，权重固定到具体 revision；换量化版本或换权重即新实验。
- 画质上限：没有做最高质量参数搜索，512–768 是证据范围，不是推荐画质。
- 性能排名：平台、编译、驱动和缓存状态未统一，仓库里的秒数不能横向比较。
- 陌生机器的全新安装验收：Windows 从零步骤是整理出的复现路径，完整安装仍待补齐；Ubuntu 有安装器，同样只在本机验证。

## 下一步

1. 装环境：[Windows 环境搭建](./02-windows-setup.md) 或 [Ubuntu + ROCm](./03-ubuntu-rocm.md)。条件允许时优先 Ubuntu，它是唯一从全新独立环境完成全链路验证的路径。
2. 验证能出图：[第一张图](./04-first-image.md)。
3. 再按需读 [模型选择](./05-models.md)、[工作流库](./06-workflows.md)、[排障](./07-troubleshooting.md)。
