# Barely Comfy

> 8GB. Almost comfortable.

RX 6650 XT · ComfyUI 实测手册：显存刚够，坑也不少。

Windows 原生 AMD 环境的真实使用记录：从环境检查、第一张图，到模型编辑、多参考输入与原生崩溃排查。**Draft · 2026-10-21**，持续整理中。

这是一台 RX 6650 XT（gfx1032，8GB VRAM）+ 16GB RAM 的单机实验，不是所有 AMD 显卡的兼容性承诺。记录成功，也保留噪声图、失败工作流、部分达到和未验证项。API 返回 success 后仍要查看图片。

## 从这里开始

1. [环境与从零搭建](docs/01-setup.md)：固定版本、AMD Python 环境、GPU 最小检查。
2. [第一张图与单项重跑](docs/02-first-image.md)：下载所需模型、提交 API 图、保存新证据。
3. [模型实测导航](docs/03-models.md)：Qwen、MOSS、Kroma、FLUX、Z-Image 与 H3 的边界。
4. [遇到的坑](docs/04-troubleshooting.md)：INT8、时间尺度、GGUF 卸载、锁页内存与 OOM。
5. [完整图文报告（GitHub 可直接阅读）](trials/2026-10-19-features/feature-report.md)。
6. [出图失败追踪与修复验证](docs/06-failure-tracker.md)：本地失败证据、上游问题及连续出图回归。
7. [未闭环功能清单](docs/07-unfinished-features.md)：排除 H3 后的 19 条待处理记录、报告漏项和配方验证欠项。
8. [实际修复重试与图片](trials/2026-10-21-repairs/README.md)：自动反推分阶段出图、FLUX 茶壶/夜景/1024 重试及仍未达标的小蝴蝶结。

[在线图文报告](https://aikiai-stack.github.io/barely-comfy/) 保留筛选与输入/输出对照。也可克隆后在本地浏览：

```powershell
git clone https://github.com/AiKiAi-stack/barely-comfy.git
cd barely-comfy
python -m http.server 8767 --bind 127.0.0.1
```

打开 <http://127.0.0.1:8767/trials/2026-10-19-features/feature-report.html>。浏览报告不需要显卡、ComfyUI 或模型权重。

## 能在这里找到什么

- 一项功能对应独立 case ID、输入、提示词、实际提交图、执行结果与目视结论。
- Qwen Image / Turbo / UN、MOSS SFT 与 8步 LoRA、Kroma Q2 的实测。
- FLUX.2 Klein 七项编辑，以及禁用锁页内存产生噪声的对照。
- Z-Image AIO 与 GGUF，9/8/4 步、中文与英文文字、连续运行的差异。
- Flux.3 的失败/来源记录，以及 H3 五帧诊断；H3 视频功能仍未验收。
- `code_source/` 的本地辅助节点，以及 `trials/` 的原始实验脚本和工作流。

![FLUX.2 Klein 实测输出](ComfyUI/output/FeatureBench/flux2-klein-single-color-pinned_00001_.png)

这张蓝包来自独立改色案例；输入、提示词与验收限制请到完整报告查看，不能单凭单张图判断编辑质量。

## 阅读约定

**执行成功 ≠ 视觉通过 ≠ 长期稳定。** 耗时区分服务启动、模型冷加载、提交后总时间和采样时间；缓存、CPU 编码、CPU VAE 与存储位置都影响结果。默认从 512 级别测试，不能把本机结果外推为 1024 或其他显卡也可用。

`trials/` 下早期 README 是历史快照，可能写有当时“尚未运行”的状态。当前总览以完整报告和对应 case 的最新结果为准，尝试过程不覆写成全部成功。

## 数据与贡献

参见 [证据结构及公开副本处理](docs/05-evidence-and-privacy.md)、[上游来源与授权范围](THIRD_PARTY_NOTICES.md) 和 [贡献说明](CONTRIBUTING.md)。仓库没有模型权重、虚拟环境、账号配置或原始文章全文。公开图片移除了文本/EXIF 元数据，视觉像素保持不变；原件校验和与公开副本校验和分开记录。

下一步：在全新 Windows 环境验证安装闭环、补充 UI 导入版工作流、补充其他显卡的独立案例。欢迎提交有图、有参数、有失败证据的复现记录。
