# 03 · 在 Ubuntu 上从零搭一套 ROCm 环境

下面记录的是在一块 RX 6650 XT 上，从全新的 Ubuntu 装出一套能出图的 ComfyUI。命令都在仓库根目录执行，安装和验证都在能直接访问 GPU 的本机终端里做。

Windows 那一套仍然有效，Ubuntu 跑通也不代表 Windows 的原生崩溃问题解决了。

## 开始之前

### 硬件、系统、驱动

这套配置在 RX 6650 XT 8GB（gfx1032）、16GB 内存、Ubuntu 22.04.5、内核 6.8.0-138 上走通。系统已经加载 amdgpu，用的是原生 gfx1032，没有设 `HSA_OVERRIDE_GFX_VERSION`。

### 内存

16GB，没有 swap。Qwen 测试的保护线是 1536MiB 可用物理内存，Z-Image 连续测试是 768MiB。触发保护是我主动停的，不算 native crash，也不是完整的 Linux OOM 保证。没有 swap，就没有额外的安全网。

### GPU 权限

你的用户要能读写 `/dev/kfd` 和 `/dev/dri/renderD*`。当时的会话是用临时 ACL 放行的，没改永久组：

```bash
ls -l /dev/kfd /dev/dri/renderD*
sudo setfacl -m u:"$(id -un)":rw /dev/kfd /dev/dri/renderD128
```

`renderD128` 只是当时的设备名，按 `ls` 的结果换成你的。重启或设备重建后 ACL 可能失效，要重新核对。设备节点对了也不代表计算能用，接着做下面的 GPU 检查。

## 这套环境钉死的版本

| 组件 | 固定值 |
| --- | --- |
| 系统 / 内核 | Ubuntu 22.04.5 / 6.8.0-138 |
| Python | 独立 Linux 3.12.14（系统 3.10 不动） |
| PyTorch | 2.12.0+rocm7.14.0 |
| torchvision | 0.27.0+rocm7.14.0 |
| ROCm / HIP | 7.14.0 / 7.14.60850 |
| ComfyUI | ce1e922d8623bb507180e32a0c01a7d0e29edef7 |
| ComfyUI-GGUF | 373048b8403a7820620065210a691263d4da0a61 |

这台机器装了 95 个锁定依赖，`pip check` 通过。记录在 [requirements-lock](../../environment/ubuntu-2026-10-23/requirements-lock.txt) 和 [GPU 计算检查](../../environment/ubuntu-2026-10-23/gpu-compute.json)。AMD 索引有一次缺 `typing-extensions==4.16.0`，安装器补了 PyPI 之后成功，torch、ROCm 和 gfx1032 的版本都没变。

不要复用 Windows 的 `.venv`。两边的解释器和二进制布局不一样。Linux 用 `runtime/ubuntu/.venv`；这台机器把同一组依赖建在 SSD 上，再让这个路径指过去。环境坏了就保留旧目录，用新的 runtime 重建，别把解释器指回 Windows。

## 1. 导出固定源码，建虚拟环境

安装器不会 clone，也不会自己去猜替代版本。它从相邻的 `amd_comfy/ComfyUI` 本地 Git 对象里用 `git archive` 导出两个固定提交，Windows 工作区里没提交的改动不会被复制。缺固定对象、缺模型目录或者缺 Linux CPython 3.12，它直接报错。

```bash
python3.12 scripts/setup_ubuntu.py \
  --source ../amd_comfy/ComfyUI \
  --models ../amd_comfy/ComfyUI/models
```

路径不一样就显式改 `--source` 和 `--models`。想让虚拟环境放 SSD，加 `--venv /绝对/SSD/路径`，安装器会建好环境，并在 `runtime/ubuntu/.venv` 留一个链接。已有 runtime 的源码版本对不上时，它会拒绝覆盖。

## 2. 装依赖

安装器按 `environment/ubuntu-2026-10-23/` 里的约束和 lock 装 torch、ROCm、ComfyUI 和 GGUF 的依赖，最后跑一遍 `pip check`。不要手工 `pip install -U` 把 GPU 栈换成别的版本。旧轮子下架了就记录失败、另开实验。

## 3. 跑 GPU 最小检查

```bash
runtime/ubuntu/.venv/bin/python scripts/check_gpu.py
```

检查在子进程里导入 torch，打印设备名和 HIP 版本，再跑一个 16×16 矩阵。必须看到 `GPU CHECK PASSED` 才能加载模型。这台机器上 FP32、FP16、BF16 的 GEMM 和 SDPA 都通过。

torch 导入时曾提示 rocSHMEM 找不到 `libnuma`，但系统里实际有 `libnuma.so.1`，这一轮的计算没受影响。这条告警保留着，别用软链接随手盖过去。

## 把模型放进去

模型权重不进仓库。放数据盘，或者从 NVMe 分区只读挂载。挂载是会话状态，重启或分区一变就可能没了。下面这条是当时用过的命令，设备号只对当时那个分区有效：

```bash
lsblk -f
udisksctl mount -b /dev/nvme0n1p2 --options ro
```

`runtime/ubuntu/model-paths.yaml` 由安装器生成，`existing_local_models.base_path` 是绝对路径，启动脚本通过 `--extra-model-paths-config` 读它。换机器、换挂载点都得改这个文件，它不会跟着仓库目录自动挪。启动前先确认里面的路径可读。NVMe 没挂上就别带着旧路径启动，否则会悄悄回退到慢盘。

后来也有把 Qwen 权重校验后复制到 SSD 的做法。不管来源，权重都不在仓库里，最终以 YAML 里的实际路径为准。

## 启动和停止服务

默认入口：

```bash
bash scripts/start_ubuntu.sh
```

它监听 `127.0.0.1:8188`，用 CPU VAE，关掉动态显存和异步卸载，保持默认锁页内存（pinned），并加载 `runtime/ubuntu/model-paths.yaml`。Windows 那边的参数结论不要照搬成 Linux 最优值。

Qwen 专用入口：

```bash
bash scripts/start_ubuntu_qwen.sh
```

它在默认参数上加了 `--fast-disk`、`--reserve-vram 1.0`、`--use-split-cross-attention`、`--force-fp16`、`--force-upcast-attention`。CPU VAE、关闭动态显存和异步卸载、默认 pinned 都继承下来。入口只是把参数固定住，不代表所有 Qwen 图都过。

同一时间只留一个 8188 服务。停止用前台 `Ctrl+C`。换入口或跑分阶段工作流之前，先停旧服务并确认端口已经放掉：

```bash
ss -ltnp | grep ':8188' || true
```

然后按对应项的说明用合适的入口重启。分阶段工作流通常要先编码，再换指定配置重启出图。两个服务的参数混着用，结果没法归因。

两个脚本都不会开机自启，重启后要重新确认 GPU ACL 和模型挂载。

## 出第一张图

服务就绪后，按 [第一张图与单项重跑](./04-first-image.md) 挑一条实际测过的 API 图，用 Linux 的解释器提交，分别记下 API 状态、history、输出 SHA 和目视结论。首次加载可能要好几分钟，别用采样时间去推算。

## 这套环境目前能跑到哪

| 项目 | 状态 |
| --- | --- |
| GPU 检查、Z-Image 同进程连续三张 | 已验证（默认 pinned、CPU VAE） |
| Qwen 指定无 LoRA 纯文本普通整图 | 部分达到：两图与两次 active `/free` 检查通过，精确细节仍部分达到 |
| Qwen 同进程连续重载 | 未通过：第二轮编码或 `/free` 触发 1536MiB 保护 |
| Qwen pinned 首次完整加载 | 未完成：停在 `pin_weight_to_device` 十多分钟，人工停止，无图 |
| 分阶段隔离 | 部分达到：规避路径，不是 native 卸载修复 |

- 默认保持 pinned。关掉锁页内存没拿到完整通过的证据，所以不作为默认值；Windows FLUX 的锁页结论也别直接搬来改 Linux。
- 分阶段的「每图新进程」只控制同时驻留的模型和激活，它不是 OOM 恢复手段，也不修 Windows 的 native 卸载故障。
- 跨平台耗时不可比。模型、精度、存储和启动参数都没完全统一，别拿 Windows 和 Ubuntu 的秒数做系统排名。
- 无 swap 时，RAM 保护是你主动停的，不要记成 native crash。1536MiB 和 768MiB 都不是完整的 OOM 保证，也别降低阈值硬跑。
- Qwen pinned 首次完整加载停在 GGUF 权重搬运之后，十多分钟没出图，也没看到 native 崩溃、OOM 或保护触发。后面指定工作流通过，不能改写这次已完成；同进程重载仍然没解决。

## 证据与出处

安装和重启的完整过程见 [2026-10-23 部署](../journal/2026-10-23-ubuntu-setup.md)、[2026-10-24 续接](../journal/2026-10-24-ubuntu-continuation.md)、[2026-10-24 重启](../journal/2026-10-24-ubuntu-reboot.md)；版本与快照见 [bootstrap](../../environment/ubuntu-2026-10-23/bootstrap.json)、[依赖锁](../../environment/ubuntu-2026-10-23/requirements-lock.txt)、[SSD 环境快照](../../environment/ubuntu-2026-10-24/snapshot.json)。

## 怎么确认这一步成功了

四件事逐条对：

1. `check_gpu.py` 打印 `GPU CHECK PASSED`，设备名是 gfx1032，HIP 版本是 7.14.60850。
2. `runtime/ubuntu/model-paths.yaml` 里的 `existing_local_models.base_path` 指向的目录能 `ls` 出来。
3. `bash scripts/start_ubuntu.sh` 起得来，`http://127.0.0.1:8188` 打得开，终端正在前台跑着。
4. [第一张图](./04-first-image.md) 那条 API 图提交后能拿到 PNG，同时你记下了 API 状态、history 和输出 SHA。

## 卡住了看哪里

- 初始化崩溃、OOM、黑图或噪声、GGUF 卸载异常：去 [遇到的坑](./07-troubleshooting.md)。
- 显卡不是 RX 6650 XT：看 [AMD 卡适配矩阵](./08-amd-matrix.md) 再决定要不要照做。
- `setfacl` 报错或 `/dev/kfd` 权限不对：先确认用户组和内核模块，别用 root 硬跑服务。
- 端口被占：`ss -ltnp | grep ':8188'` 找出进程，先停掉再启动。
- 模型路径读不到：先 `lsblk -f` 确认分区还在、挂载点还在，再改 YAML。
