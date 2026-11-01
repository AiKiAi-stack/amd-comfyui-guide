<div align="center">

<img src="assets/banner.zh.webp" alt="AMD 显卡 ComfyUI 指南。小卡，整张图。" width="100%">

# AMD 显卡 ComfyUI 指南

**小卡，整张图。**

在 AMD 显卡上从驱动装到第一张图，每个结果都留了记录。

[English](README.md) · [简体中文](README.zh-CN.md)

[![Check tutorial snapshot](https://github.com/AiKiAi-stack/amd-comfyui-guide/actions/workflows/check-publication.yml/badge.svg)](https://github.com/AiKiAi-stack/amd-comfyui-guide/actions/workflows/check-publication.yml)
[![Latest release](https://img.shields.io/github/v/release/AiKiAi-stack/amd-comfyui-guide?label=release)](https://github.com/AiKiAi-stack/amd-comfyui-guide/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

</div>

---

## 这是什么

你手上有一张 AMD 显卡，想让 ComfyUI 在它上面跑起来。这份指南带你装完 Windows 10 或 Ubuntu 22.04.5，出第一张图，再告诉你 40 项 ComfyUI 功能里哪些能在 8 GB 显存上真的跑通。每项功能都有独立记录：输入、提示词、工作流、输出图、耗时和结论，失败的也留着。

所有结论来自一台机器：AMD Radeon RX 6650 XT（gfx1032），8 GB 显存，16 GB 内存，Windows 10 与 Ubuntu 22.04.5，ROCm 7.14、PyTorch 2.12.0、ComfyUI `ce1e922`。Windows 和 Linux 的记录分开存，两组结果不是同一个测试。

这张卡是证据来源，不是读者范围。你的卡不是它，先读 [AMD 显卡适配矩阵](docs/tutorial/08-amd-matrix.md)，看自己落在哪一档。

## 实测结果

<!-- STATS:START -->
| 指标 | 数值 |
|---|---:|
| 模型系列 | 7 |
| 功能记录 | 40 |
| 平台记录 | 162（95 Windows + 67 Linux） |
| 工作流 | 268 UI + 268 API · 已安装 184 |
| 记录案例 | 88 |
<!-- STATS:END -->

<img src="assets/features.webp" alt="RX 6650 XT 上的四张真实出图：Qwen Image 2.1 Turbo、FLUX.2 Klein、Kroma Q2、MOSS SFT" width="100%">

[完整功能报告](https://aikiai-stack.github.io/amd-comfyui-guide/)有 40 张卡片，每张都带输入、提示词、真实输出、耗时和各平台结论。

## 快速开始

1. **先对配置。** [硬件、系统与版本](docs/tutorial/01-hardware.md)开头就是对照表。卡不是 RX 6650 XT，先读[适配矩阵](docs/tutorial/08-amd-matrix.md)再动手装。
2. **装环境。** [Windows](docs/tutorial/02-windows-setup.md) 或 [Ubuntu + ROCm](docs/tutorial/03-ubuntu-rocm.md)。Ubuntu 是唯一从全新独立环境走完整套流程的路径。
3. **出一张图。** 跟着[第一张图](docs/tutorial/04-first-image.md)走一遍，然后从[工作流库](docs/tutorial/06-workflows.md)挑一份工作流。

手上没有 AMD 卡也能看：[功能报告](https://aikiai-stack.github.io/amd-comfyui-guide/)不需要模型权重。

## 工作流库

268 份 WebUI 工作流，每份配一个 API 文件，全部在真实的 ComfyUI 前端里导入导出核对过。两个包：

- [完整包，约 360 MiB](https://github.com/AiKiAi-stack/amd-comfyui-guide/releases/download/model-feature-workflows-2026-10-26/model-feature-workflows.zip)：工作流、输入图片，以及核对过的编码文件。
- [轻量包，约 12 MiB](https://github.com/AiKiAi-stack/amd-comfyui-guide/releases/download/model-feature-workflows-2026-10-26/model-feature-workflows-light.zip)：只有工作流，编码步骤自己跑。

安装步骤、文件命名和 SHA 注意事项在[工作流库](docs/tutorial/06-workflows.md)那一章。

## 教程

按顺序读。前提是卡已经装进机器、驱动已经就位。

| 章节 | 什么时候读 |
|---|---|
| [01 硬件、系统与版本](docs/tutorial/01-hardware.md) | 装之前先确认显卡、系统、版本的组合 |
| [02 Windows 环境搭建](docs/tutorial/02-windows-setup.md) | 在 Windows 上用原生 AMD 环境 |
| [03 Ubuntu + ROCm](docs/tutorial/03-ubuntu-rocm.md) | 已验证的路径，从全新环境开始 |
| [04 第一张图](docs/tutorial/04-first-image.md) | 验证 GPU 真的能出图 |
| [05 模型](docs/tutorial/05-models.md) | 挑一个模型系列，把权重放到位 |
| [06 工作流库](docs/tutorial/06-workflows.md) | 下载、导入、复现一项结果 |
| [07 排障](docs/tutorial/07-troubleshooting.md) | 初始化崩溃、OOM、黑图、噪声图 |
| [08 AMD 卡适配矩阵](docs/tutorial/08-amd-matrix.md) | 把指南套用到别的 AMD 卡 |

完整文档索引在 [docs/](docs/README.md)。

## 证据怎么读

四件事分开记录：工作流能打开、实际出图、达到目标、连续重复还稳定。四者不能互相顶替。失败和部分达到的结果刻意留在记录里，你的卡出现同样现象时，多半要回来翻这些。

先看[证据结构与公开副本](docs/reference/evidence-and-privacy.md)和[故障追踪与根因边界](docs/reference/failure-tracker.md)。报告没有引用的原始实验归档在 [barely-comfy-evidence](https://github.com/AiKiAi-stack/barely-comfy-evidence)，附 SHA256 清单。

## 仓库结构

```
docs/         教程（tutorial）、参考（reference）、日志（journal）
evidence/     功能报告、case 与平台记录
workflows/    268 份 UI + API 工作流、catalog 与下载包
scripts/      安装、重放与校验脚本
environment/  固定版本与硬件记录
assets/       README 与站点视觉素材（由真实出图构建）
```

## 相关项目

- **[ming-tts-webui](https://github.com/AiKiAi-stack/ming-tts-webui)**：Ming-3.0-TTS 本地语音工作台（Gradio + FastAPI，AMD ROCm），单独一个仓库。

## 参与贡献

最有价值的贡献是在别的 AMD 卡上复现一遍。带上输入、提示词、工作流、输出、耗时和失败证据。动手之前先看 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 许可证

[MIT](LICENSE)。第三方来源和上游授权见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
