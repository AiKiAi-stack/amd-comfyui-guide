# Ubuntu 续接记录 · 2026-10-24

本文追加 `handoff.md` 之后的 Linux 实测。Windows 的历史结论、环境及模型文件均保留；本轮不将 Linux 成功解释为 Windows 原生卸载故障已修复。

## 环境和存储

重启后重新检查并临时授予当前用户 `/dev/kfd`、`/dev/dri/renderD128` 的读写 ACL。它不是永久组配置，重启后需重新核对。

共享的“系统”盘实际是机械硬盘。Linux venv 位于该 NTFS 盘时，Torch 导入曾在文件页读取等待中停留数分钟。将**相同的 95 个依赖版本**重建到系统 SSD 的 `/home/user/.local/share/barely-comfy/ubuntu-20261024/.venv`，`pip check` 通过，GPU 小运算通过，Torch 导入约 2.123 秒。当前项目 `runtime/ubuntu/.venv` 为指向它的软链接；原 Linux 环境保存在 `.venv.ntfs-20261023`，Windows 环境未动。未完成的复制目录 `.venv.copy-incomplete` 不是可用环境。

安装器的 AMD 下载源缺少 lock 所需的 `typing-extensions==4.16.0`，首次新建失败。给 AMD 安装阶段补充 PyPI 作为依赖源后成功；Torch/ROCm/gfx1032 固定版本未变。版本及 GPU 证据见 [SSD 环境](../../evidence/2026-10-24-ubuntu/ssd-environment.json)、[GPU 检查](../../evidence/2026-10-24-ubuntu/ssd-gpu-check.json)。

安装器现支持 `--venv /绝对/SSD路径` 建立独立环境并链接到 runtime，以及显式 `--gguf-cpu-detach` 应用本轮补丁。默认不自动启用该补丁；已有环境若指向其他位置会拒绝覆盖。重复安装保留已有 `model-paths.yaml`，避免覆盖人工核验的 NVMe 配置；本次 `--skip-install` 续接检查退出0，配置 SHA 前后相同，见 [续接检查](../../evidence/2026-10-24-ubuntu/setup-resume-check.json)。

已有 NVMe 分区 GIAO 通过 `udisksctl mount -b /dev/nvme0n1p2 --options ro` **只读挂载**到 `/media/user/GIAO`。复用其中的 `AIModels/amd_comfy/repair-20261021`、`zimage-20261020`、`flux2-klein-20261020`；Qwen/Z-Image 所需 7 个文件重新计算 SHA，与原模型一致，见 [模型校验](../../evidence/2026-10-24-ubuntu/nvme-model-hashes.json)。

当前 `runtime/ubuntu/model-paths.yaml` 优先索引上述 NVMe 目录，原 HDD 路径保留作为补充；原配置在 `model-paths.hdd-20261023.yaml`。挂载是本次会话状态，不保证重启后存在；若 NVMe 未挂载，先按实际分区重新只读挂载，再启动，避免悄悄回退到慢盘。源码仍在共享盘，故此项不是纯粹的单变量性能基准。

## Qwen 加载：分别记录存储、代码和内存边界

1. SSD Python + NVMe 模型、**未改 GGUF**：仍停在文本编码器加载。`replay_workflow.py` 的单次 HTTP 请求等待 60 秒后超时，整个尝试约 96.95 秒；它不是设置的 480 秒工作流总时限。服务由控制器停止，无图片，未观察到 native/OOM。见 [基线补记](../../evidence/2026-10-24-ubuntu/qwen-stock-nvme-result.json)。因此不能把换盘单独称为 Qwen 加载修复。
2. 原 CPU detach 测试的 ≤1MiB Q4_K fixture 不存在，旧 `StopIteration` 仅是 fixture 失败。本轮改为实际存在、≤16MiB 的最小真实 Q4_K 张量。未修改 GGUF 在实际 `pin_weight_to_device` 回调中请求 GPU staging，受控测试明确失败；候选及实际 Linux 副本通过。测试核对独立 CPU 存储、原始量化 bytes/hash、GGML 类型/形状/patches、bias/buffer、重复 pin；不会写入只读 mmap。
3. [CPU detach 补丁](../../scripts/apply_gguf_cpu_detach_patch.py) 只把 CUDA load / CPU offload 时的 mmap 解映射改为独立 CPU 复制，保留普通路径和源备份；不修改 unpatch/OOM 清理。只应用于 `runtime/ubuntu/ComfyUI/custom_nodes/ComfyUI-GGUF/nodes.py`，Windows 及仓库归档原件未替换。[补丁 hash 与范围](../../evidence/2026-10-24-ubuntu/cpu-detach-runtime-patch.json)。
4. 相同默认精度工作流加补丁后，文本编码器完成加载并进入扩散加载，随后物理内存保护在约 1.1GiB 可用时停止。保护阈值仍为 1536MiB；没有降低保护硬跑，也没有图片。原始 summary 留有 running，以 [停止补记](../../evidence/2026-10-24-ubuntu/qwen-default-cast-guard-result.json) 为准。日志为 BF16 权重、FP32 manual cast；这说明后续仍有独立的容量/精度问题，不能宣称完整修复。

原 10 月 23 日 no-pin 尝试也没有完成编码，退出清理曾超时；保留旧 raw 文件，在 [结果补记](../../evidence/2026-10-24-ubuntu/qwen-20261023-no-pin-result-supplement.json) 澄清遗留 running。关闭锁页并未得到完整通过证据。

## 报告补卡

补齐 `qwen-multiref-full-tail` 的 HTML 索引和卡片，卡片总数 100 → 101；Markdown 只追加。保留“部分达到”、尾部仍出框、精确身份未证明、背景来自局部合成的原评价。全部旧 100 张 article 的字节保持一致，新卡片 prompt/history 和 3 张公开图的 SHA 已核对。[修改证明](../../evidence/2026-10-24-ubuntu/report-repair.json)、[新审计](../../evidence/2026-10-24-ubuntu/backlog-audit.json)。49 条未闭环记录仍包含重复尝试，不是 49 个独立功能。

随后发现原报告50个案例的已有输出因 `D:/AI/.../ComfyUI/output/...` 在 Ubuntu 上不可解析而显示为空。修正构建器的跨平台路径映射，并在 HTML/Markdown **追加历史输出图库**，不重建原卡片；原101张 article 字节均不变，图片与原 result 路径后缀绑定，全部 HTML 图片链接存在。这些是已有 Windows 图片，不是本轮 Linux 重新生成。[图库绑定和 SHA](../../evidence/2026-10-24-ubuntu/report-path-gallery.json)。以后完整重建会由修正后的解析器在原输出面板显示它们；本次未全量重建或修改历史结论。

## 完整出图与释放验证

使用 [本轮运行器](../../evidence/2026-10-24-ubuntu/run_qwen_phases.py) 在一个自有服务中依次执行编码、保存并校验条件 archive、真实 `/free`、采样并保存有限 latent、真实 `/free`、CPU VAE 解码、真实 `/free`；改变眼睛颜色提示和 seed 后重跑。每阶段记录实际 API/history/SHA，最初要求 reserved ≤256MiB；严格检查的失败及后续显式 active 检查见实验页，物理内存阈值 1536MiB 不变。

采样显式 FP16 + attention upcast，512²、15 步、CFG1、Euler/simple、Qwen cache off、默认 pinned，关闭动态显存和异步卸载。它与默认 FP32 manual cast 的基线不是逐像素等价承诺。最终结果及目视记录追加在本目录实验页。

目前可用规避路径是每张图一个新进程；每次只传一个 workflow，使用全新输出目录，且确认 8190 无其他服务。同进程两轮及堆回收对照均触发RAM保护，不能当作已验收命令：

```bash
runtime/ubuntu/.venv/bin/python evidence/2026-10-24-ubuntu/run_qwen_phases.py \
  --out runs/ubuntu-qwen-single-new --free-check active \
  --workflow evidence/2026-10-23-ubuntu/workflows/qwen-reload-02.api.json
```

这条分阶段路径用于控制同时驻留的模型和激活；不是“一张原始大图直接提交即可完成”的保证，也不是异常/OOM 恢复或 Windows Kroma native 问题的验收。CPU backing 候选继续默认关闭；身份、LoRA 消融、CPU 反推、FLUX 细节等历史待办不因环境可启动而自动完成。

## 主机内存后续对照

第一张完整 Qwen 已完成，但没有额外主机堆回收时，第二轮编码触发1536MiB RAM保护。一次只重放已有latent的CPU解码小探针，在空闲时执行 GC 和 `malloc_trim(0)`，RSS从约3.3GB逐步降到约1.1GB，见 [实验页](../../evidence/2026-10-24-ubuntu/README.md)。这是显式实验，不修改Torch、不卸载仍被引用的张量，也没有降低物理内存保护。

运行器以 `--host-trim --stack-hook evidence/2026-10-24-ubuntu/diagnostics` 单独启用该对照；信号钩子仅存在于自有实验服务。严格reserved释放检查失败记录仍保留；`--free-check active` 只检查有效占用并完整保存缓存指标。默认 `scripts/start_ubuntu.sh` 不启用此堆回收实验。当前95个依赖及运行源码SHA在 [10月24日环境快照](../../environment/ubuntu-2026-10-24/snapshot.json)。

完整对照未解决连续重载：第二轮编码47.78秒完成，但之后 `/free` 的CPU内存峰值仍触发1536MiB保护，最后采样可用内存约297MiB；自有进程退出0，不能据此称OOM/原生崩溃。前一轮完整图片健康通过，但与未trim图不逐像素相同；差异没有归因隔离。[失败摘要](../../evidence/2026-10-24-ubuntu/qwen-host-trim-result.json)、[实际回收量](../../evidence/2026-10-24-ubuntu/qwen-host-trim-measurements.json)、[图片差异测量](../../evidence/2026-10-24-ubuntu/first-image-trim-comparison.json)。因此堆回收保持实验选项，不推广成默认修复；后续独立进程出图是明确规避。

纯文本编码的VAE是可选且未被核心读取，新增两项实际核心契约测试通过；保守的 `--omit-unused-vae` 只优化已知无参考输入，不改解码或任何参考图。实际整模型对照首轮编码后 `/free` 仍触发保护，无新PNG，[结果](../../evidence/2026-10-24-ubuntu/qwen-no-unused-vae-result.json)。它也不是卸载修复，默认关闭。当前完整图证据是蓝图及独立进程绿图；绿图编码52.06秒、采样316.13秒、解码13.01秒，服务正常退出0，[绑定与目视](../../evidence/2026-10-24-ubuntu/qwen-green-isolated/result.json)。两图健康正常，但提示细节仍部分达到，同进程连续重载继续未通过。

## 最终回归及交付状态

CPU detach副本下Z-Image同进程连续红/蓝壶2/2执行成功、2/2目视通过，每轮文本和采样均重跑，[绑定](../../evidence/2026-10-24-ubuntu/zimage-repeat/summary.json)、[目视](../../evidence/2026-10-24-ubuntu/zimage-reviews.json)。原30项加CPU detach两项、无参考VAE两项，本轮34项回归通过。原100张报告卡片与review文件保留证明见 [校验](../../evidence/2026-10-24-ubuntu/preservation-check.json)，新增图库后仍101张卡片、没有漏卡。

实验服务均已停止，默认服务已在 <http://127.0.0.1:8188/> 启动；HTML、GPU状态和所需节点均验证，浏览器主画布已显示，[服务检查](../../evidence/2026-10-24-ubuntu/service-liveness.json)。报告在 <http://127.0.0.1:8767/evidence/2026-10-19-features/feature-report.html>。二者只监听本机，无开机自启；重启后重新确认GPU ACL和NVMe只读挂载。[最终结果索引](../../evidence/2026-10-24-ubuntu/outcomes.json)。

剩余优先项仍是Qwen同进程卸载/重载的主机内存峰值、Windows Kroma候选的完整验收、精确身份/LoRA消融及CPU反推、FLUX细节；本轮没有把它们修改为通过，也没有对外发布。
