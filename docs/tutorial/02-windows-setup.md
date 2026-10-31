# 02 · 在 Windows 上搭一套 AMD 环境

下面从头装一套能出图的 ComfyUI：AMD 显卡、Python 3.12、ROCm 版 PyTorch。装完就能进 [第一张图](./04-first-image.md)。

我现有的 Windows 环境是早就装好的，这一轮没有推倒重装，所以下面这些从零步骤是根据当前版本快照整理出来的复现路径，整套全新安装的验收还等着补齐。另外，包能装上不等于 GPU 能用，第 3 步的检查别跳过。

## 开始之前

- 硬件按这台机器的配置来：RX 6650 XT 8GB（gfx1032）、16GB 内存、Python 3.12.6。
- 装好 Git、Python 3.12 x64，以及 AMD 官网给你的那张卡对应的驱动。
- 模型、虚拟环境、缓存都建议放在 D: 这类空间充足的盘。
- 下面拿 `D:\AI` 当项目父目录，克隆出来的目录叫 `amd-comfyui-guide`。换成你自己的路径就行；我当时的记录用的是 `D:\AI\barely-comfy`。

## 1. 建独立目录

先建目录、拉仓库、建虚拟环境：

```powershell
New-Item -ItemType Directory -Force D:\AI | Out-Null
Set-Location D:\AI
git clone https://github.com/AiKiAi-stack/amd-comfyui-guide.git
Set-Location amd-comfyui-guide
py -3.12 -m venv .venv
$env:PIP_CACHE_DIR = 'D:\AI\cache\pip'
$env:HF_HOME = 'D:\AI\cache\huggingface'
```

仓库里的 `ComfyUI/input` 和 `ComfyUI/output` 是公开的证据素材，所以别直接往这个非空目录 clone。源码单独放一份，证据输入之后复制过去：

```powershell
git clone https://github.com/Comfy-Org/ComfyUI.git runtime/ComfyUI
git -C runtime/ComfyUI checkout ce1e922d8623bb507180e32a0c01a7d0e29edef7
git clone https://github.com/city96/ComfyUI-GGUF.git runtime/ComfyUI/custom_nodes/ComfyUI-GGUF
git -C runtime/ComfyUI/custom_nodes/ComfyUI-GGUF checkout 373048b8403a7820620065210a691263d4da0a61
```

## 2. 装 AMD 版 PyTorch

按 [TheRock 上游的 multi-arch 安装说明](https://github.com/ROCm/TheRock/blob/main/docs/packaging/legacy_multi_arch_releases.md)，用与版本匹配的 AMD 索引，并且选 `device-gfx1032`。索引内容会变，装到最新的包不等于复现了我这套。

装之前先对照 [安装来源记录](../../environment/install-provenance.md)，确认那几个版本还能拿到，再把这一组 torch、torchvision、torchaudio、rocm 装上。旧版本下架了，就记录新版本、重新开一次实验，不要不声不响换成 CUDA 包或别的 ROCm 版本。

装 ComfyUI 的 Python 依赖时带上版本约束，免得解析器把 GPU 栈换掉：

```powershell
.venv\Scripts\python.exe -m pip install -r runtime/ComfyUI/requirements.txt -c environment/amd-constraints.txt
.venv\Scripts\python.exe -m pip install -r runtime/ComfyUI/custom_nodes/ComfyUI-GGUF/requirements.txt -c environment/amd-constraints.txt
.venv\Scripts\python.exe -m pip install requests psutil pillow
```

## 3. 先检查 GPU，再启动 ComfyUI

跑这一个脚本：

```powershell
.venv\Scripts\python.exe scripts/check_gpu.py
```

它会在子进程里导入 torch，查显卡信息，再做一次小的 GPU 张量运算。你必须看到设备名、HIP 版本和计算通过。原生 `0xC0000005` 或 access violation 这种崩溃，普通的 Python try/except 是救不回来的，失败就停在这一步。

早先那套独立的 ROCm 7.2 / torch 2.9.1 环境在 GPU 初始化就崩，它不是现在这些成功图所用的环境。两个版本别混着配。

## 4. 装上两个本地辅助节点

```powershell
Copy-Item code_source/gfx1032_quant_fallback runtime/ComfyUI/custom_nodes -Recurse
Copy-Item code_source/feature_bench_ordering runtime/ComfyUI/custom_nodes -Recurse
```

第一个节点默认关闭，只有同时满足 HIP、gfx1032 和 `COMFY_GFX1032_INT8_FALLBACK=1` 时，才绕开原生 INT8 GEMM，改走 ComfyUI 自带的浮点反量化路径。第二个只负责安排批次编码的依赖顺序，不混提示词。两个都不是所有模型通用的加速插件。

## 证据与出处

版本、包快照和索引可用性都在 [environment](../../environment/) 目录：先看 [安装来源记录](../../environment/install-provenance.md)，再看 [包快照](../../environment/packages.json)。

## 怎么确认这一步成功了

三件事同时成立才算装好：

1. `python scripts/check_gpu.py` 打印出设备名和 HIP 版本，并且计算通过。
2. `pip freeze` 里 torch 是 `2.12.0+rocm7.14.0`，`torchvision` 是 `0.27.0+rocm7.14.0`，`torchaudio` 是 `2.11.0+rocm7.14.0`。
3. ComfyUI 和 ComfyUI-GGUF 的提交分别等于 `ce1e922d8623bb507180e32a0c01a7d0e29edef7` 和 `373048b8403a7820620065210a691263d4da0a61`。

三条都对上，接着去 [第一张图](./04-first-image.md)。

## 卡住了看哪里

- `check_gpu.py` 崩在初始化：别往下装模型，这是 GPU 栈的问题。先回 [安装来源记录](../../environment/install-provenance.md) 对版本。
- 装依赖时 torch 被换掉了：漏了 `-c environment/amd-constraints.txt`，重装一遍。
- 想省硬盘换了路径：命令里的 `D:\AI` 全部改成你的实际路径，`PIP_CACHE_DIR` 和 `HF_HOME` 也一样。
- 环境搭好了还是不出图：去 [排障](./07-troubleshooting.md)，先对照 `torch.cuda.is_available()` 那一段。
