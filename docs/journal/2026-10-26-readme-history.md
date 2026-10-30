# 早期README记录

以下保留各阶段的说明与计数，当前范围和入口以仓库首页为准。

# Barely Comfy

> 8GB. Almost comfortable.

RX 6650 XT · ComfyUI 实测手册：显存刚够，坑也不少。

Windows 原生 AMD 环境的真实使用记录：从环境检查、第一张图，到模型编辑、多参考输入与原生崩溃排查。**Draft · 2026-10-21**，持续整理中。

这是一台 RX 6650 XT（gfx1032，8GB VRAM）+ 16GB RAM 的单机实验，不是所有 AMD 显卡的兼容性承诺。记录成功，也保留噪声图、失败工作流、部分达到和未验证项。API 返回 success 后仍要查看图片。

## 从这里开始

1. [环境与从零搭建](../tutorial/02-windows-setup.md)：固定版本、AMD Python 环境、GPU 最小检查。
2. [第一张图与单项重跑](../tutorial/04-first-image.md)：下载所需模型、提交 API 图、保存新证据。
4. [遇到的坑](../tutorial/07-troubleshooting.md)：INT8、时间尺度、GGUF 卸载、锁页内存与 OOM。
5. [完整图文报告（GitHub 可直接阅读）](../../evidence/2026-10-19-features/feature-report.md)。
6. [出图失败追踪与修复验证](../reference/failure-tracker.md)：本地失败证据、上游问题及连续出图回归。
8. [实际修复重试与图片](../../evidence/2026-10-21-repairs/README.md)：自动反推分阶段出图、FLUX 茶壶/夜景/1024 重试及仍未达标的小蝴蝶结。

[在线图文报告](https://aikiai-stack.github.io/barely-comfy/) 保留筛选与输入/输出对照。也可克隆后在本地浏览：

```powershell
git clone https://github.com/AiKiAi-stack/barely-comfy.git
cd barely-comfy
python -m http.server 8767 --bind 127.0.0.1
```

打开 <http://127.0.0.1:8767/evidence/2026-10-19-features/feature-report.html>。浏览报告不需要显卡、ComfyUI 或模型权重。

## 能在这里找到什么

- 一项功能对应独立 case ID、输入、提示词、实际提交图、执行结果与目视结论。
- Qwen Image / Turbo / UN、MOSS SFT 与 8步 LoRA、Kroma Q2 的实测。
- FLUX.2 Klein 七项编辑，以及禁用锁页内存产生噪声的对照。
- Z-Image AIO 与 GGUF，9/8/4 步、中文与英文文字、连续运行的差异。
- `code_source/` 的本地辅助节点，以及 `evidence/` 的原始实验脚本和工作流。

![FLUX.2 Klein 实测输出](../../ComfyUI/output/FeatureBench/flux2-klein-single-color-pinned_00001_.png)

这张蓝包来自独立改色案例；输入、提示词与验收限制请到完整报告查看，不能单凭单张图判断编辑质量。

最新持续排障见 [2026-10-22 解决过程](2026-10-22-repair-journal.md)，包含失败假设、实际改动、条件复用校验和逐项图片结论。

## 阅读约定

**执行成功 ≠ 视觉通过 ≠ 长期稳定。** 耗时区分服务启动、模型冷加载、提交后总时间和采样时间；缓存、CPU 编码、CPU VAE 与存储位置都影响结果。默认从 512 级别测试，不能把本机结果外推为 1024 或其他显卡也可用。

`evidence/` 下早期 README 是历史快照，可能写有当时“尚未运行”的状态。当前总览以完整报告和对应 case 的最新结果为准，尝试过程不覆写成全部成功。

## 数据与贡献

参见 [证据结构及公开副本处理](../reference/evidence-and-privacy.md)、[上游来源与授权范围](../../THIRD_PARTY_NOTICES.md) 和 [贡献说明](../../CONTRIBUTING.md)。仓库没有模型权重、虚拟环境、账号配置或原始文章全文。公开图片移除了文本/EXIF 元数据，视觉像素保持不变；原件校验和与公开副本校验和分开记录。

下一步：在全新 Windows 环境验证安装闭环、补充 UI 导入版工作流、补充其他显卡的独立案例。欢迎提交有图、有参数、有失败证据的复现记录。

## 2026-10-23 追加：Ubuntu 本机部署

新增 [Ubuntu 安装、启动和验证记录](2026-10-23-ubuntu-setup.md)，使用独立 Linux 运行目录并复用现有模型。Windows 的历史结论及未闭环事项保留；新的 Linux 结果见 [独立试验](../../evidence/2026-10-23-ubuntu/README.md)。

## Ubuntu 续接（2026-10-24 追加）

SSD 独立环境、只读 NVMe 模型复用、Qwen CPU detach 前后对照、内存保护及报告补卡见 [续接记录](2026-10-24-ubuntu-continuation.md)。Windows 原结论保留；完整出图和释放验收以该日新增实验记录为准。

### Ubuntu 2026-10-24 重启后续接追加

Linux Python 已迁到独立 SSD 基础运行库，95 个依赖版本不变；Qwen 四份模型校验复制到 SSD 并完整读回核对。指定无 LoRA 的纯文本普通整图已在同一进程连续两张 512×512、15 步出图与真实卸载检查通过。原 Windows 结论不改。

Qwen 入口为 `bash scripts/start_ubuntu_qwen.sh`，普通启动脚本保留原默认参数。使用 [蓝色工作流](../../evidence/2026-10-24-ubuntu-followup/qwen-ubuntu-blue.api.json) 或 [绿色工作流](../../evidence/2026-10-24-ubuntu-followup/qwen-ubuntu-green.api.json)。参数、失败边界、图片、当前服务与剩余项见 [续接记录](2026-10-24-ubuntu-reboot.md)。

## 模型 / 功能 / Windows 与 Linux 对照（2026-10-24 追加）

[新版 HTML 汇报](../../evidence/2026-10-19-features/feature-report.html) 现在按模型、功能分组，并列展示 Windows / Linux 的结果、原评价和复现步骤。9 个模型/权重系列、46 个功能分组；未验证平台明确保留。原 Windows 报告和评价不改写。

[工作流库](../../workflows/README.md) 已整理 99 份经过前端回环核对的 WebUI JSON，按模型 / 功能安装到本机左侧“工作流 → 模型功能库”；报告可下载单份或完整输入包。Linux 已执行预设与 Windows 历史配方分开标明，导入通过不等于 Linux 执行通过。Qwen 蓝眼预设额外经过本轮实际 WebUI 出图复核。

[本轮说明与校验证据](2026-10-24-platform-report.md)。本地汇报地址不变；本次未发布线上站点。

## Linux功能补图与工作流更新（2026-10-25追加）

[模型/功能/平台汇报](../../evidence/2026-10-19-features/feature-report.html) 已补42张Linux实测图，40/47功能组有Linux输出；9系列、169条证据。Windows原101条评价和完整归档保留，Linux不足仍按实际标注。

[模型功能库](../../workflows/README.md) 共268份真实前端回环通过的UI，184份已安装。新Linux优先使用编码/采样阶段图；4B辅助反推方案为反推/编码/采样三阶段，归档随完整包提供，修改输入后按说明重跑。完整包约360.1MiB，轻量包约11.7MiB。

44项回归、图片/归档绑定、下载包CRC、桌面/手机与安装文件可见性通过；真实WebUI排队一张采样图成功。8188与8767已恢复，重启后仍需核对挂载/GPU访问。完整边界与复现见[本轮说明](2026-10-25-linux-coverage.md)和[证据](../../evidence/2026-10-24-linux-coverage/README.md)。未关闭旧Windows卸载/身份/LoRA消融、原8B CPU反推、视频或OOM待办。

### 2026-10-25 平台证据修订

当前为 **8 个模型系列、41 个功能组、163 条证据，Linux 40 组有图**；按本卡适用范围缩减模型后，95 条 Windows 历史评价和案例卡片保持原样。新版每组增加条件对照、计时范围及 Linux 问题的已确认原因、未确认根因、已验证方案和未完成工作。此前秒数未完整控制变量，不能解读成操作系统加速倍数。详见 [审计说明](2026-10-25-report-audit.md)。

### 2026-10-26 报告精简

默认显示当前结果、图片和工作流；测试过程收起，展开后按先后说明每次测试的目的、改动和结果。状态用语统一，Windows原评价不改。[修订说明](2026-10-26-report-reading.md)；

### 当前报告（2026-10-26）

保留7个实测模型系列、40项功能。Linux为21项通过、18项部分达到、1项未达到；Windows原评价保留。页面可按结果筛选，搜索条件随网址保存；旧测试按方案展开。[打开报告](../../evidence/2026-10-19-features/feature-report.html) · [使用工作流](../../workflows/README.md)。
