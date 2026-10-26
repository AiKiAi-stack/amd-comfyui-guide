# Barely Comfy

在RX 6650 XT（8GB显存、16GB内存）上部署ComfyUI，记录Windows和Ubuntu的实际运行结果。

[打开功能报告](trials/2026-10-19-features/feature-report.html) · [使用工作流](workflows/README.md) · [Ubuntu安装与启动](docs/09-ubuntu-setup-2026-10-23.md)

当前保留7个模型系列、40项功能。Linux有21项通过、18项部分达到、1项未达到；40项均有输出图片。Windows的95条原评价与案例保留在报告中。

报告默认显示当前结果和图片。展开“测试过程”可查看每个方案为什么测、改了什么、结果如何。搜索和结果筛选随网址保存，刷新后可恢复。

## 查看报告

浏览报告不需要显卡或模型。克隆仓库后运行：

```bash
git clone https://github.com/AiKiAi-stack/barely-comfy.git
cd barely-comfy
python -m http.server 8767 --bind 127.0.0.1
```

打开 <http://127.0.0.1:8767/trials/2026-10-19-features/feature-report.html>。

## 使用ComfyUI工作流

本库提供268份经过前端导入检查的UI工作流及对应API，本机已安装184份推荐工作流。完整包包含输入图片和编码结果，不含模型权重；在其他机器上使用或修改输入前，请看[工作流说明](workflows/README.md)。

需要分步运行的方案，必须按该项说明切换启动配置。工作流能打开、实际出图、达到目标和长期稳定分别记录，不互相替代。两平台配置没有完全统一，耗时不能用于系统速度排名。

## 文档与原始记录

- [Windows安装记录](docs/01-setup.md)、[第一张图](docs/02-first-image.md)
- [故障与修复](docs/06-failure-tracker.md)、[当前报告说明](docs/16-report-polish-2026-10-26.md)
- [Windows原始图文报告](trials/2026-10-19-features/feature-report.md)、[早期进展](docs/17-readme-history-2026-10-26.md)
- [公开副本与数据处理](docs/05-evidence-and-privacy.md)、[上游授权](THIRD_PARTY_NOTICES.md)、[贡献说明](CONTRIBUTING.md)

仓库不包含模型权重、虚拟环境、账号配置或文章全文。原始模型测试图和结论按各次记录保留。

## 独立语音 WebUI

[Ming-3.0-TTS-0.5B 本地语音工作台](standalone/ming-tts-webui/README.md)：Docker Compose部署的Gradio页面，提供内置音色、声音克隆、长文分段和本机API。
