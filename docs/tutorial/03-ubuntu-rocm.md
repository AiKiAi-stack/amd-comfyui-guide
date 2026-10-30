# 03 · Ubuntu + ROCm 环境搭建

本章记录在本机 Ubuntu 上建立独立 ComfyUI 环境的过程。Windows 环境与结论保留；Ubuntu 成功不用于关闭 Windows 原生崩溃问题。以下命令在仓库根执行，安装和验证都在能直接访问 GPU 的本机终端进行。

## 适用范围与前置条件

- **已验证**：RX 6650 XT 8GB（gfx1032）、16GB RAM、Ubuntu 22.04.5、内核 6.8.0-138。系统已加载 amdgpu，使用原生 gfx1032，未设 `HSA_OVERRIDE_GFX_VERSION`。
- **内存约束**：16GB、无 swap。Qwen 测试的保护线是 1536MiB 可用物理内存，Z-Image 连续测试是 768MiB。触发保护是主动停止，不等于 native crash，也不是完整的 Linux OOM 保证；无 swap 不提供额外安全网。
- **GPU 权限**：当前用户要能读写 `/dev/kfd` 和 `/dev/dri/renderD*`。历史会话用临时 ACL 放行，没有改永久组：

```bash
ls -l /dev/kfd /dev/dri/renderD*
sudo setfacl -m u:"$(id -un)":rw /dev/kfd /dev/dri/renderD128
```

`renderD128` 只是当时的设备名，按 `ls` 结果替换。重启或设备重建后 ACL 可能失效，要重新核对。设备节点正确也不代表计算通过，继续做 GPU 检查。

## 固定版本

| 组件 | 本机固定值 |
| --- | --- |
| 系统 / 内核 | Ubuntu 22.04.5 / 6.8.0-138 |
| Python | 独立 Linux 3.12.14（系统 3.10 不动） |
| PyTorch | 2.12.0+rocm7.14.0 |
| torchvision | 0.27.0+rocm7.14.0 |
| ROCm / HIP | 7.14.0 / 7.14.60850 |
| ComfyUI | ce1e922d8623bb507180e32a0c01a7d0e29edef7 |
| ComfyUI-GGUF | 373048b8403a7820620065210a691263d4da0a61 |

本机实际安装 95 个锁定依赖，`pip check` 通过，记录见 [requirements-lock](../../environment/ubuntu-2026-10-23/requirements-lock.txt) 与 [GPU 计算检查](../../environment/ubuntu-2026-10-23/gpu-compute.json)。AMD 索引曾缺 `typing-extensions==4.16.0`，安装器补 PyPI 后成功，torch/ROCm/gfx1032 版本未变。

不要复用 Windows `.venv`：两边的解释器和二进制布局不同。Linux 使用 `runtime/ubuntu/.venv`；本机把同一组依赖建在 SSD，并让该路径指向它。环境损坏时保留旧目录，用新的 runtime 重建；不要把解释器指回 Windows。

## 安装步骤

### 1. 准备固定源码与模型目录

安装器不会 clone，也不会自动寻找替代版本。它从相邻 `amd_comfy/ComfyUI` 的本地 Git 对象用 `git archive` 导出两个固定提交，不复制 Windows 工作区未提交的改动。缺固定对象、模型目录或 Linux CPython 3.12 时直接报错。

```bash
python3.12 scripts/setup_ubuntu.py \
  --source ../amd_comfy/ComfyUI \
  --models ../amd_comfy/ComfyUI/models
```

路径不同就显式改 `--source` / `--models`。希望虚拟环境放 SSD 时加 `--venv /绝对/SSD/路径`；安装器会建立环境并在 `runtime/ubuntu/.venv` 留链接。已有 runtime 的源码版本不一致时会拒绝覆盖。

### 2. 依赖

安装器按 `environment/ubuntu-2026-10-23/` 的约束和 lock 安装 torch、ROCm、ComfyUI 与 GGUF 依赖，再跑 `pip check`。不要手工 `pip install -U` 把 GPU 栈换成别的版本；旧轮子下架时应记录失败并新建实验。

### 3. GPU 最小检查

```bash
runtime/ubuntu/.venv/bin/python scripts/check_gpu.py
```

检查在子进程导入 torch，打印设备名和 HIP 版本，再执行 16×16 矩阵。必须看到 `GPU CHECK PASSED` 才能加载模型。本机 FP32/FP16/BF16 的 GEMM 与 SDPA 均通过。torch 导入曾提示 rocSHMEM 找不到 `libnuma`，系统实际已有 `libnuma.so.1`，本轮计算未受影响；保留原告警，不用随意软链接掩盖。

## 模型放置

模型权重不进入仓库。权重放在数据盘，或从 NVMe 分区只读挂载；挂载是会话状态，重启或分区变化后可能不存在。历史命令如下，设备号只对当时分区有效：

```bash
lsblk -f
udisksctl mount -b /dev/nvme0n1p2 --options ro
```

`runtime/ubuntu/model-paths.yaml` 由安装器生成，`existing_local_models.base_path` 是绝对路径，启动脚本通过 `--extra-model-paths-config` 读取。换机器、换挂载点后必须改这个文件；它不会随仓库目录移动自动更新。启动前先确认配置里的路径可读，NVMe 没挂上时不要带着旧路径启动，以免悄悄回退到慢盘。后来也有把 Qwen 权重校验复制到 SSD 的做法；无论来源，权重都不在仓库，最终以 YAML 的实际路径为准。

## 启动与停止

默认入口：

```bash
bash scripts/start_ubuntu.sh
```

它监听 `127.0.0.1:8188`，使用 CPU VAE，关闭动态显存和异步卸载，保持默认锁页内存（pinned），并加载 `runtime/ubuntu/model-paths.yaml`。不要照搬 Windows 的参数结论当 Linux 最优值。

Qwen 专用入口：

```bash
bash scripts/start_ubuntu_qwen.sh
```

它在默认参数上增加 `--fast-disk`、`--reserve-vram 1.0`、`--use-split-cross-attention`、`--force-fp16`、`--force-upcast-attention`，CPU VAE、关闭动态显存/异步卸载和默认 pinned 仍继承。入口只固定参数，不代表所有 Qwen 图都通过。

同一时间只保留一个 8188 服务。停止用前台 `Ctrl+C`；切换入口或跑分阶段工作流前，先停旧服务并确认端口已释放：

```bash
ss -ltnp | grep ':8188' || true
```

再按该项说明用对应入口重启。分阶段工作流通常要求先完成编码，再以指定配置重启后出图；混用两个服务的参数会得到无法归因的结果。两个脚本都不会开机自启，重启后要重新确认 GPU ACL 和模型挂载。

## 验证第一张图

服务就绪后，按 [第一张图与单项重跑](./04-first-image.md) 选择一条实际测试过的 API 图，用 Linux 解释器提交，并分别记录 API 状态、history、输出 SHA 和目视结论。首次加载可能数分钟，不能用采样时间推算。

## 已知限制

| 项目 | 状态 |
| --- | --- |
| GPU 检查、Z-Image 同进程连续三张 | 已验证（默认 pinned、CPU VAE） |
| Qwen 指定无 LoRA 纯文本普通整图 | 部分达到：两图与两次 active `/free` 检查通过，精确细节仍部分达到 |
| Qwen 同进程连续重载 | 未通过：第二轮编码或 `/free` 触发 1536MiB 保护 |
| Qwen pinned 首次完整加载 | 未完成：停在 `pin_weight_to_device` 十多分钟，人工停止，无图 |
| 分阶段隔离 | 部分达到：规避路径，不是 native 卸载修复 |

- 默认保持 pinned。关闭锁页内存未得到完整通过证据，不作为默认；不要用 Windows FLUX 的锁页结论直接改 Linux。
- 分阶段“每图新进程”只控制同时驻留的模型和激活，不是 OOM/异常恢复，也不修复 Windows 的 native 卸载故障。
- 跨平台耗时不可比较：模型、精度、存储和启动参数没有完全统一，不能拿 Windows/Ubuntu 秒数做系统排名。
- 无 swap 时 RAM 保护是操作者主动停止，不记成 native crash；1536MiB/768MiB 都不是完整 OOM 保证，不应降低阈值硬跑。
- Qwen pinned 首次完整加载停在 GGUF 权重搬运后，十多分钟无图，未观察到 native/OOM/保护触发。后续指定工作流通过不能改写成这次已完成；同进程重载仍未解决。

## 排障与延伸

- 初始化崩溃、OOM、黑图/噪声、GGUF 卸载异常：见 [遇到的坑](./07-troubleshooting.md)。
- 显卡不是 RX 6650 XT 时如何套用：见 [AMD 卡适配矩阵](./08-amd-matrix.md)。
- 安装、续接与重启的完整过程：[2026-10-23 部署](../journal/2026-10-23-ubuntu-setup.md)、[2026-10-24 续接](../journal/2026-10-24-ubuntu-continuation.md)、[2026-10-24 重启](../journal/2026-10-24-ubuntu-reboot.md)。
- 版本与证据：[bootstrap](../../environment/ubuntu-2026-10-23/bootstrap.json)、[依赖锁](../../environment/ubuntu-2026-10-23/requirements-lock.txt)、[SSD 环境快照](../../environment/ubuntu-2026-10-24/snapshot.json)。
