# 01 · 显卡、系统和版本

这一章不装任何东西。你只要确认一件事：手上这台机器，能不能照着后面的章节走。

我把整套流程跑通的机器只有一台，显卡是 RX 6650 XT。下面这张表就是它。你的机器对得上，后面每一章都可以直接照做；对不上，先看 [AMD 显卡适配矩阵](./08-amd-matrix.md)，别急着开始装。

## 这套配置长什么样

| 项目 | Windows | Ubuntu（从零走完全程） |
| --- | --- | --- |
| 显卡 | AMD Radeon RX 6650 XT（gfx1032） | 同左 |
| 显存 | 8 GB（ComfyUI 报告 8,176 MB） | 8 GB（8,573,157,376 字节） |
| 内存 | 16 GB（16,197 MB） | 16 GB，无 swap |
| 系统 / 内核 | Windows 10.0.19045 | Ubuntu 22.04.5 / 6.8.0-138-generic |
| 显卡驱动 | AMD 32.0.21045.5002 | amdgpu（随内核） |
| Python | 3.12.6 | 3.12.14（系统 3.10 未替换） |
| ROCm / HIP | 7.14.0 | 7.14.0 / 7.14.60850 |
| torch | 2.12.0+rocm7.14.0 | 2.12.0+rocm7.14.0 |
| ComfyUI | ce1e922d8623bb507180e32a0c01a7d0e29edef7 | 同左 |
| ComfyUI-GGUF | 373048b8403a7820620065210a691263d4da0a61 | 同左 |

Windows 那边还装了 torchaudio 2.11.0+rocm7.14.0，Linux 没装。两个平台的 torchvision 都是 0.27.0+rocm7.14.0。

系统名有个小出入。`machine.json` 记的是 `Microsoft Windows 10 家庭版`、版本 10.0.19045，而教程里其他章节按 Windows 11 来写。表按元数据填，系统版本我没有单独再核。

装好之后，先在 ComfyUI 源码目录核对这两个提交：

```bash
# 在 ComfyUI 源码目录执行
git rev-parse HEAD
git -C custom_nodes/ComfyUI-GGUF rev-parse HEAD
```

对不上表里的值，就别拿后面的图当参照，先把版本对齐。

## 8GB 显存在这里意味着什么

主力尺寸是 512×512。768 只出现在早期基线和个别 Windows 记录里，比如 Qwen Base 的 768 文生图、旧的 768² 16 步基线，不是默认值。

分阶段隔离是常规手段。文本编码、采样、CPU 解码各开一个进程，条件和 latent 通过归档传下去，具体见 [三阶段运行器](../../scripts/run_conditioned_repair.py) 和 [Qwen 参考阶段](../../scripts/run_qwen_reference_repair.py)。CPU VAE 默认打开（[start_ubuntu.sh](../../scripts/start_ubuntu.sh) 里的 `--cpu-vae`），拿时间换显存。

1024 只在个案里成立。FLUX 1024 采样能跑完，到 CPU 解码时撞上内存保护，把 tile 改成 256、overlap 改成 64 分块解码才拿到图；Kroma 参考链内部升到 1024 时 OOM 了。所以别说「8GB 能跑 1024」。

长任务也按个案看。Z-Image 同一个进程连着跑三张是过的；Qwen pinned 第一次完整加载跑了十多分钟没完成，我人工停了。一次成功不能当成长期稳定。

## Windows 和 Ubuntu 各走到哪一步

两个平台合计 162 条记录，Windows 95 条，Linux 67 条。

Windows 那 95 条是原评价和案例、GPU 检查、分阶段规避和 768 基线。现在能看的成功图来自 ROCm 7.14 环境。更早那套独立的 ROCm 7.2 + torch 2.9.1，在 `torch.cuda.is_available()` 就出 access violation，至今没修，两套不能混着说。本机还留着早期 ROCm 7.2 包的安装元数据，那不代表旧栈能用。

Ubuntu 22.04.5 + ROCm 7.14 是唯一从全新独立环境走完「安装 → GPU 检查 → 出图 → 连续生成 → 回归」的一条路：Linux 40 项功能里 21 项通过、18 项部分达到、1 项没达到。

这不代表 Windows 不能用，也不代表 Ubuntu 换台机器一定成。两个平台的提示词、编码器、精度和进程方式都不一样，耗时不能拿来排名。

## 这份指南不覆盖的部分

- 别的显卡：只在 [AMD 显卡适配矩阵](./08-amd-matrix.md) 里分「已验证 / 同架构未验证 / 未验证」三档，没测过的卡我不做兼容承诺。
- 别的模型权重：只测了 7 个模型系列、40 项功能，权重都钉在具体 revision 上。换量化版本或换权重，都是新实验。
- 画质上限：没做过最高质量参数搜索。512 到 768 是证据范围，不是推荐画质。
- 性能排名：平台、编译、驱动和缓存状态都没统一，文里的秒数不能横向比。
- 陌生机器上的全新安装验收：Windows 的从零步骤是整理出来的复现路径，完整安装还等着补齐；Ubuntu 有安装器，同样只在这台机器上验过。

## 证据与出处

表里的数值和记录都在 [machine.json](../../environment/machine.json)、[Windows 安装来源](../../environment/install-provenance.md)、[Windows 包快照](../../environment/packages.json)、[Ubuntu 环境记录](../../environment/ubuntu-2026-10-23/)、[GPU 计算检查](../../environment/ubuntu-2026-10-23/gpu-compute.json) 和 [Ubuntu 部署日志](../journal/2026-10-23-ubuntu-setup.md) 里。

## 怎么确认这一步成功了

三件事都能答上来，这一章就过了。

1. 你的显卡和系统能在表里找到对应行，或者你知道它落在 08 章的哪一档。
2. 装完环境后，`git rev-parse HEAD` 出来的提交和表里一致。
3. 你清楚 512×512 是这套记录的主力尺寸，768 和 1024 都要单独试。

三条都对上，就可以开始装环境了：Windows 走 [Windows 环境搭建](./02-windows-setup.md)，Linux 走 [Ubuntu + ROCm](./03-ubuntu-rocm.md)，条件允许优先 Ubuntu，它是唯一从全新独立环境走完全程的路径。装完用 [第一张图](./04-first-image.md) 验一次，再按需读 [模型选择](./05-models.md)、[工作流库](./06-workflows.md) 和 [排障](./07-troubleshooting.md)。

## 卡住了看哪里

- 不知道自己卡的代号：装好驱动后跑 `rocminfo | grep gfx`，完整做法见 [AMD 显卡适配矩阵](./08-amd-matrix.md)。
- 提交号对不上：先把版本换成表里的提交，或者把差异单独记一次，别在旧结论上接着跑。
- 显卡不是 RX 6650 XT：直接读 08 章，这里没有你的答案。
- 想知道某个数字是怎么来的：翻「证据与出处」里列的那几个文件。
