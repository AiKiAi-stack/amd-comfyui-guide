# 安装来源与版本锁定

2026-10-20 读取现有环境的 Python 包元数据，未重新安装。`packages.json` 仅含包名和版本，不含 pip 配置、凭据或本机安装路径。ComfyUI / GGUF Git 工作区本轮检查为干净。

实际使用版本：Python 3.12.6、torch 2.12.0+rocm7.14.0、torchvision 0.27.0+rocm7.14.0、torchaudio 2.11.0+rocm7.14.0、rocm/rocm-sdk-core 7.14.0，以及对应 gfx1032 device 包。

已实时核对 AMD 稳定 multi-arch 索引中存在匹配 Windows CPython 3.12 的 torch、torchvision、torchaudio、gfx1032 device wheel。索引可用性记录见 `index-availability.json`，这不等于重新安装验收通过。

以下为固定版本安装命令，安装前先建独立环境；版本下架时应报错并记录，而不是自动升级：

```powershell
.venv\Scripts\python.exe -m pip install --index-url https://repo.amd.com/rocm/whl-multi-arch/ "torch[device-gfx1032]==2.12.0+rocm7.14.0" "torchvision[device-gfx1032]==0.27.0+rocm7.14.0" "torchaudio==2.11.0+rocm7.14.0" "rocm[libraries,devel,device-gfx1032]==7.14.0"
```

随后按教程安装 ComfyUI 依赖、运行最小 GPU 检查。首次新机器安装、显卡驱动安装及重新生成图片尚待独立验收。

参考：[AMD TheRock 历史索引说明](https://github.com/ROCm/TheRock/blob/main/docs/packaging/legacy_multi_arch_releases.md)、[AMD 稳定包索引](https://repo.amd.com/rocm/whl-multi-arch/)。本机仍留有一项早期 ROCm 7.2 自定义库包的安装元数据；它不证明旧栈已经成功，也不能从现状推导严格最小依赖集合。完整包快照保留此事实，后续应在干净环境中做减依赖验证。
