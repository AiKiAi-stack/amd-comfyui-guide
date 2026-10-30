# 02 · Windows 环境与从零搭建

## 已确认的实测环境

Windows、RX 6650 XT 8GB（gfx1032）、16GB RAM，Python 3.12.6。当前本机包元数据为 `torch 2.12.0+rocm7.14.0`、`torchvision 0.27.0+rocm7.14.0`、`torchaudio 2.11.0+rocm7.14.0`。精确包快照见 [environment](../../environment/)。ComfyUI 固定提交 `ce1e922d8623bb507180e32a0c01a7d0e29edef7`，GGUF 插件固定提交 `373048b8403a7820620065210a691263d4da0a61`。

本仓库的图片来自已有环境。本轮没有重新安装整套 GPU 环境；以下从零步骤是依据当前版本快照整理的复现路径，完整全新安装验收仍待补齐。不要把“能安装包”当成 GPU 已可用。

## 1. 准备独立目录

安装 Git、Python 3.12 x64 与适用于自己系统的 AMD 显卡驱动。模型、虚拟环境和缓存建议放 D: 或其他空间充足的磁盘。本文假定仓库在 `D:\AI\barely-comfy`。

```powershell
New-Item -ItemType Directory -Force D:\AI | Out-Null
Set-Location D:\AI
git clone https://github.com/AiKiAi-stack/amd-comfyui-guide.git
Set-Location barely-comfy
py -3.12 -m venv .venv
$env:PIP_CACHE_DIR = 'D:\AI\cache\pip'
$env:HF_HOME = 'D:\AI\cache\huggingface'
```

本仓库的 `ComfyUI/input` 与 `ComfyUI/output` 只是公开证据素材，所以不要直接向该非空目录 git clone。先建立单独源码目录，再复制证据输入：

```powershell
git clone https://github.com/Comfy-Org/ComfyUI.git runtime/ComfyUI
git -C runtime/ComfyUI checkout ce1e922d8623bb507180e32a0c01a7d0e29edef7
git clone https://github.com/city96/ComfyUI-GGUF.git runtime/ComfyUI/custom_nodes/ComfyUI-GGUF
git -C runtime/ComfyUI/custom_nodes/ComfyUI-GGUF checkout 373048b8403a7820620065210a691263d4da0a61
```

## 2. AMD PyTorch

根据 [TheRock 上游历史 multi-arch 安装说明](https://github.com/ROCm/TheRock/blob/main/docs/packaging/legacy_multi_arch_releases.md)，使用与版本匹配的 AMD 索引及 `device-gfx1032`。当前索引会变化，不能直接安装最新包并称为复现本实验。

本地实际安装包版本与可用索引检查见 [安装来源记录](../../environment/install-provenance.md)。先按该记录确认版本仍可取得，再安装同一组 torch / torchvision / torchaudio / rocm 包。若旧版本已下架，应记录新版本并建立新实验，不静默换成 CUDA 包或其他 ROCm 版本。

安装 ComfyUI Python 依赖时使用已验证 AMD 包的版本约束，防止依赖解析替换 GPU 栈：

```powershell
.venv\Scripts\python.exe -m pip install -r runtime/ComfyUI/requirements.txt -c environment/amd-constraints.txt
.venv\Scripts\python.exe -m pip install -r runtime/ComfyUI/custom_nodes/ComfyUI-GGUF/requirements.txt -c environment/amd-constraints.txt
.venv\Scripts\python.exe -m pip install requests psutil pillow
```

## 3. 先检查 GPU，再启动 ComfyUI

```powershell
.venv\Scripts\python.exe scripts/check_gpu.py
```

检查会在子进程中导入 torch，查询显卡并执行小型 GPU 张量运算。必须看到设备名称、HIP 版本和计算通过。原生 `0xC0000005` / access violation 无法用普通 Python try/except 修复，失败时先停在这里。

之前独立 ROCm 7.2 / torch 2.9.1 环境在 GPU 初始化就崩溃；它不是当前成功图片所用环境。不要把两个版本混用。

## 4. 安装本地辅助节点

```powershell
Copy-Item code_source/gfx1032_quant_fallback runtime/ComfyUI/custom_nodes -Recurse
Copy-Item code_source/feature_bench_ordering runtime/ComfyUI/custom_nodes -Recurse
```

第一个节点默认关闭，仅在 HIP + gfx1032 + `COMFY_GFX1032_INT8_FALLBACK=1` 时绕开原生 INT8 GEMM，采用 ComfyUI 已有反量化路径。第二个节点只安排批次编码依赖，不混合提示词。它们不是所有模型通用的加速插件。

继续 [首次出图](04-first-image.md)。
