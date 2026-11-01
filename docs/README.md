# 文档索引

本目录是 AMD ComfyUI Guide 的文档区。教程按顺序读，参考材料按需查，实验日志按日期留。

## 教程（按顺序）

| # | 章节 | 适合什么时候读 |
| --- | --- | --- |
| 01 | [先确认能不能照做](tutorial/01-hardware.md) | 装之前判断你的卡适不适合照做 |
| 02 | [在 Windows 上搭一套 AMD 环境](tutorial/02-windows-setup.md) | 在 Windows 10/11 上使用原生 AMD 环境 |
| 03 | [在 Ubuntu 上从零搭一套 ROCm 环境](tutorial/03-ubuntu-rocm.md) | 从零建立独立环境（唯一完整验证过的路径） |
| 04 | [出第一张图，再单独重跑一项](tutorial/04-first-image.md) | 装完后验证 GPU 与工作流是否真的能出图 |
| 05 | [挑一个模型：各系列实测到什么程度](tutorial/05-models.md) | 下载、放置模型，并按实测范围缩小选择 |
| 06 | [工作流库：下载、导入、复现](tutorial/06-workflows.md) | 下载或导入 268 份工作流并复现结果 |
| 07 | [遇到的坑：按症状排障](tutorial/07-troubleshooting.md) | 初始化崩溃、OOM、黑图等问题怎么看、怎么办 |
| 08 | [换一张 AMD 卡怎么套用](tutorial/08-amd-matrix.md) | 实测卡以外的卡要改什么 |

## 参考材料

- [实测环境](reference/test-machine.md)：本次实测机器的配置、平台覆盖与固定版本，教程里引用的数字都在这里对得上。
- [证据结构与公开副本](reference/evidence-and-privacy.md)：图片去元数据、校验和与发布规则。
- [故障追踪与根因边界](reference/failure-tracker.md)：运行错误编号与「已确认 / 未确认」的划分。
- [模型来源与配方审计](reference/research/)：模型来源、第三方配方、兼容性调研。

## 实验日志

- [按日期索引](journal/README.md)：每次实验的背景、改动、结果与停止原因。

## 其他入口

- [工作流库说明](../workflows/README.md)
- [功能报告（本地）](../report/index.html) · [在线报告](https://aikiai-stack.github.io/amd-comfyui-guide/)
- [贡献指南](../CONTRIBUTING.md) · [第三方说明](../THIRD_PARTY_NOTICES.md)
