# Ubuntu 本机部署 · 2026-10-23

这是新增的 Linux 实验线。Windows 文档、失败证据和既有结论继续保留；Ubuntu 的成功不用于关闭 Windows 原生崩溃。当前仓库原有的 11 个未提交修改文件已在迁移前记录 SHA，本轮不覆盖。

## 目录与版本

- `runtime/ubuntu/.venv`：独立 Linux Python 3.12 环境，首次使用本机 Codex 附带的 Python 3.12.14 建立；系统 Python 3.10 和旧 Windows `.venv` 不变。
- `runtime/ubuntu/ComfyUI`：从旧本地 Git 对象导出固定提交 `ce1e922d8623bb507180e32a0c01a7d0e29edef7`，GGUF 固定 `373048b8403a7820620065210a691263d4da0a61`。不复制旧工作区未提交源码改动。
- PyTorch `2.12.0+rocm7.14.0`、torchvision `0.27.0+rocm7.14.0`、ROCm `7.14.0`，使用原生 `device-gfx1032`。没有设置 `HSA_OVERRIDE_GFX_VERSION`。本轮未安装非必需的 torchaudio/devel。
- 本地辅助节点单独复制到新运行目录；只在该副本应用已有的 attention 奇数查询切片补丁，并保留原文件和 SHA。INT8/GGUF 候选规避插件默认不开启。

[包快照](../../environment/ubuntu-2026-10-23/packages.json)、[依赖锁](../../environment/ubuntu-2026-10-23/requirements-lock.txt)、[GPU 计算](../../environment/ubuntu-2026-10-23/gpu-compute.json)、[模型 SHA](../../environment/ubuntu-2026-10-23/model-hashes.json) 和 [回归测试](../../environment/ubuntu-2026-10-23/regression-tests.json) 分别记录。

## GPU 权限

Ubuntu 22.04.5、内核 6.8.0-138 已加载 amdgpu，但本次登录的 wbb 无权打开 `/dev/kfd`。经用户授权执行了临时 ACL：

```bash
sudo setfacl -m u:"$(id -un)":rw /dev/kfd /dev/dri/renderD128
```

没有修改永久组权限。重启或设备重新创建后需要重新授予 ACL。Codex 沙箱本身隐藏 GPU 设备，即使主机会话 ACL 正确，GPU 检查和启动仍须在有设备访问的本机终端或已授权的沙箱外执行。

## 安装与启动

在本仓库目录，用 Linux Python 3.12 执行：

```bash
python3.12 scripts/setup_ubuntu.py
runtime/ubuntu/.venv/bin/python scripts/check_gpu.py
bash scripts/start_ubuntu.sh
```

安装器从相邻 `amd_comfy/ComfyUI` 的本地 Git 固定提交导出源码；目录不同时指定 `--source /path/to/ComfyUI --models /path/to/models`。不存在固定提交、模型目录或 CPython 3.12 时会报错，不升级替代。安装命令使用 AMD 官方索引与 PyPI，并约束本轮依赖版本。系统没有 `python3.12` 时须先提供一个 Linux Python 3.12；本机首次使用的解释器路径见 `bootstrap.json`。

界面是 <http://127.0.0.1:8188>，仅监听本机。默认 GPU 编码/采样、CPU VAE、关闭动态显存与异步卸载，保持锁页内存默认值。不要把 Windows 的参数结论当作 Linux 已验证的最优配置。

## 验证及继续工作

GPU 最小检查通过，FP32/FP16/BF16 GEMM 与 SDPA 均通过。系统已有 `libnuma.so.1`，但 torch 导入时 rocSHMEM 仍提示找不到 `libnuma`；它没有阻止本轮计算，保留原日志，不改系统库链接来隐藏提示。

连续出图、卸载诊断及目视结果见 [Ubuntu 独立试验记录](../../trials/2026-10-23-ubuntu/README.md)。原始日志和完整 history 留在被忽略的 `runs/ubuntu-*`，精选输出与摘要另存到新的 trial 目录。

当前主机 16GB RAM、无 swap；连续测试显式设置 768MiB 物理可用内存保护。触发保护属于主动停止，不记录成 native crash。该保护不是 Linux OOM 的完整保证。

继续顺序：Linux 连续生成及量化卸载 → Qwen 独立重载回归 → 精确身份保持/参考消融 → CPU 编码特定配置。

安装依据：[AMD TheRock 历史 multi-arch 索引](https://github.com/ROCm/TheRock/blob/main/docs/packaging/legacy_multi_arch_releases.md)、[官方安装与设备选择说明](https://github.com/ROCm/TheRock/blob/main/RELEASES.md)。能安装设备包不等于 GPU 计算已通过，本轮分别做了实测。
