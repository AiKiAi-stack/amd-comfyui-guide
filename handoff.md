# Barely Comfy 双系统开发交接

更新日期：2026-10-24。用途：在同一台机器的 Ubuntu 上继续开发时，补齐无法继承的 Windows Codex 会话上下文。本文件汇总可检索的相关会话，并以磁盘上的源码、工作流、history、结果和评价校正旧说法。

**当前并未解决所有问题。** 已有多项完整出图和部分代码修复；分阶段运行是有效规避；精确身份迁移、部分配方验证、CPU 大模型反推、完整模型卸载和异常恢复仍有欠项。Linux 与 Windows 的结果必须分别登记。

## 1. 先找对目录

这是同一台 RX 6650 XT 机器的 Windows / Ubuntu 双系统，数据文件已经能从 Ubuntu 直接访问，**不需要重新搬迁或下载整个项目**。盘符是历史定位信息，Ubuntu 中应使用挂载后的路径。

共享目录的相对关系：

```text
MyProject/
├── amd_comfy/                       原始实验、Windows 环境、模型、原图
│   ├── handoff.md                   本文的项目入口副本
│   ├── .venv/                      Windows Python，不能当 Linux 环境使用
│   ├── ComfyUI/                    原始完整源码与 models/input/output
│   ├── research/
│   ├── prompt-gallery/
└── comfyui-rx6650xt-lab/             实际 Git 仓库，远程名 barely-comfy
    ├── handoff.md                   本文的代码仓库主本
    ├── code_source/                自编辅助节点
    ├── scripts/                    重放、隔离、诊断、验证脚本
    ├── docs/                       教程、问题清单、修复日记、Ubuntu 说明
    ├── environment/                版本和安装来源
    ├── research/                   模型来源和配方审计
    ├── trials/                     精选公开证据，含失败与部分达到
    ├── ComfyUI/input,output/        公开素材，并非完整 ComfyUI 安装
    ├── runtime/ubuntu/             已建立的独立 Linux 环境，Git 忽略
    └── runs/                       原始修复日志、张量归档、临时控制器，Git 忽略
```

以下命令均从 **`comfyui-rx6650xt-lab` 仓库根目录**运行。若当前在 `amd_comfy`，先 `cd ../comfyui-rx6650xt-lab`。本文主本中的文件链接也相对于仓库根；项目入口副本已调整链接。

上一轮 Ubuntu 的共享盘挂载位置是 `/media/user/系统/MyProject/`，这只是历史实例，不应硬编码为所有登录会话都不变的路径。先用 `pwd`、`findmnt -T .` 确认当前挂载点；带空格或中文的路径始终加引号。

Windows 侧还使用了 G 盘 NVMe 的现有副本：`G:/AIModels/amd_comfy/{repair-20261021,flux2-klein-20261020,zimage-20261020}`，以及 `G:/ComfyRepairRuntime/venv-20261021`。Ubuntu 需要这些文件时找到对应分区挂载点，重写模型搜索 YAML，不能直接使用 `G:/...`。这不意味着所有模型只在 G 盘；先核对实际配置及 SHA，避免重复下载。

## 2. 项目目标和必须延续的验收口径

- 项目是 **Barely Comfy — 8GB. Almost comfortable.**，分享 RX 6650 XT 8GB / 16GB RAM 上 ComfyUI 的真实使用、搭建步骤、失败与规避，仍是持续完善中的教程实验仓库。
- 用户最看重 **feature → output image 一一对应**。一个案例应有独立输入、提示词、模型/配方、实际执行图、输出、耗时和视觉判断；不能拿其他功能或其他模型的成功图补位。
- 区分四件事：程序执行成功、图像目标通过、同进程连续运行通过、底层根因修复。API `success` 也可能是噪声、黑图、错误物种或身份不符。
- 保留历史失败、部分结果、无输出和停止原因。人工停止、内存保护停止、超时、Python 异常、OOM、原生访问冲突分别记；若保护停止前已有 native 栈，两者都记录。
- 分阶段隔离、CPU VAE、降参考分辨率、最终遮罩合成都是明确的配方或规避，不能写成通用模型能力或 native 修复。遮罩外零变化通常来自最终合成。
- 固定来源和版本；作者整合包、公开量化组合、普通版与 UN、不同编码器要分开。没有同条件对照时，不宣称 UN 更强；没有参考消融时，不宣称参考身份已生效。
- 不为测试而停止其他项目的服务。只管理本次启动并能确认归属的进程；不按旧 PID 文件盲目恢复或结束进程。
- 模型、缓存和大日志留在数据盘。公开仓库不上传账户、凭据、私人素材、原始文章全文或未经筛选的实验内容。参考 [证据与隐私](docs/reference/evidence-and-privacy.md)、[第三方说明](THIRD_PARTY_NOTICES.md)。
- 用户要求新会话按 `[YY-MM-DD] 会话主题` 命名；能自主推进的工作直接推进，只有实质影响结果的选择才询问。

## 3. 已检查的会话及各自贡献

当前项目 `Comfy_in_AMD` 下有 4 个相关 Codex 会话，另有 2 个直接关联的来源/续跑会话。此次读取了它们可检索的全部回合页；未将其他项目的聊天混入。会话 ID 供原设备查询，Ubuntu 不必能打开这些聊天，下面的结论和文件足以继续工作。

1. **[26-10-18] 复现 AMD RX6600XT ComfyUI ROCm**，`01a14ae7-0407-7150-98c1-754a424a2237`。标题写 RX6600XT，实际硬件为 RX6650XT。复现 Linux.do 文章中的 Windows ROCm 7.2 初始化崩溃；另建 7.14 环境成功运行 GPU 检查、SD1.5、Qwen Image 2.1。Qwen 最初遇到 GGUF 架构不识别，曾改用 leejet 分支；后续实验应以固定提交记录为准。还从 PromptHero/OpenArt/Lexica 各取原文提示词，得到三张经目视的 768²、16 步图；原始来源、API 和运行索引在 `../amd_comfy/prompt-gallery/`。
6. **[26-10-20] 下载微信公众号文章**，`01a13a1b-01a1-75e3-ba33-9e5dc7e43fe3`。两篇 Z-Image 正文离线保存，分别是“托尼不是塔克”的 AIO（2025-12-11）和 GGUF（2025-12-01）文章，共 26 张图片；来源包历史 Windows 位置 `[private-article-snapshot]`，有 `index.html`、Markdown、原网页、验证文件、下载脚本和 ZIP。原正文是本地研究资料，不是公开仓库内容。

来源导航见 [模型来源](docs/reference/research/liuyue-five-model-trial-sources.md)、[功能声明](docs/reference/research/feature-claims-2026-10-19.md)、[新文章](docs/reference/research/new-articles-2026-10-20.md)。旧会话的耗时、服务“已恢复”等是当时状态，不能代替现在检查。

## 4. Git 状态：Ubuntu 接手时先保留工作区

- 远程：[AiKiAi-stack/barely-comfy](https://github.com/AiKiAi-stack/barely-comfy)。本地目录仍叫 `comfyui-rx6650xt-lab`；`amd_comfy` 不是 Git 仓库。
- 当前分支：`fix/gguf-repeat-stability`；HEAD：`a6f531db38b0d948233f44a6ea24d9d32e72983a`。此次交接检查时，与本地保存的 `origin/fix/gguf-repeat-stability` 比较为 ahead 0 / behind 0；本轮没有 fetch，不代表重新核验了远端。
- 关键已有提交：`c84986e` MOSS 入口防护与 GGUF 连续证据；`fac35ad` 待办核对/CPU 反推补漏；`3bb4de4` 有界 caption 和 FLUX 重试；`96d6f12` attention/部分输出；`a6f531d` 参考 VAE 隔离。旧会话记录这些提交当时已推送并通过 CI，本次没有重跑远端 CI。
- **存在大量未提交的修改与未跟踪文件，同一共享工作区中的这些内容比 GitHub 分支更新。** 不要 `reset --hard`、`clean`，也不应另行 clone 后只看已提交版本。
- 已修改包括 README、docs/07、docs/08、`probe_quantized_offload.py`、`repro_gguf_repeat.py`、`run_qwen_reference_repair.py`、`run_repair_batch.py`、图测试/参考验证和主报告 JSON/HTML/MD。
- 未跟踪的重要内容：`gguf_mmap_offload`、`gguf_unload_trace`、CPU caption 工具、Ubuntu 安装/启动工具和说明、`test_gguf_cpu_detach.py`、Ubuntu 环境记录、10月22/23新证据、九个新修复案例及公开图片、多个尚未跑完的工作流。
- `runs/`、`runtime/`、虚拟环境和模型权重被 `.gitignore` 忽略；“Git 没变化/没跟踪”不表示它们可删除。它们在双系统共享盘上，可以直接访问。

接手先读：`git status --short --branch`、`git diff --stat`、`git log -5 --oneline`。本次仅整理交接，不替这些 WIP 做统一提交、推送、重装或重新下载。

## 5. 已有文档与证据入口

建议先读本文件，再读 07、08、09，然后看具体案例。

- [README](README.md)：定位、公开入口和总导航；[贡献方式](CONTRIBUTING.md)；[许可证](LICENSE)。公开站点是 https://aikiai-stack.github.io/barely-comfy/ ，不应假定它已经包含本地 WIP。
- [01 搭建](docs/tutorial/02-windows-setup.md)：Windows 版本、隔离安装和 GPU 检查。它不是 Ubuntu 安装教程，也不是全新陌生机器已验收的保证。
- [02 首图](docs/tutorial/04-first-image.md)、[03 模型导航](docs/tutorial/05-models.md)、[04 排障](docs/tutorial/07-troubleshooting.md)、[05 证据隐私](docs/reference/evidence-and-privacy.md)。03 是较早概览，一些“部分达到”后来已有独立重试，应结合 07/08 和最新 case。
- [06 故障追踪](docs/reference/failure-tracker.md)：BC-001—014，运行错误与根因边界；[07 未闭环功能](docs/journal/2026-10-21-unfinished-features.md)：19 条历史基线与配方缺口；[08 解决过程日记](docs/journal/2026-10-22-repair-journal.md)：E01—E09，含假设、对照、成功、失败和后续。
- [09 Ubuntu 本机部署](docs/journal/2026-10-23-ubuntu-setup.md)：Linux 独立环境、GPU 权限、固定版本、启动及测试限制。
- [总图文报告](trials/2026-10-19-features/feature-report.html) / [Markdown](trials/2026-10-19-features/feature-report.md)：主功能索引；同目录 `cases.json`、`baseline.json`、`blocked.json`、`reviews.json` 和每项 `cases/<id>/result.json` 是核对材料。
- [首轮步骤](trials/2026-10-18/STEP_BY_STEP.md) / [首轮实测](trials/2026-10-18/README.md)；[FLUX.2](trials/2026-10-20-flux2-klein/README.md)；[Z-Image](trials/2026-10-20-zimage/README.md)；[Windows 11 张连续测试](trials/2026-10-21-gguf-repeat/README.md)。
- [实际修复重试](trials/2026-10-21-repairs/README.md)：图片、conditions/latent/phase-link、失败 attempts；[修复过程证据](trials/2026-10-22-unload/README.md)；[扩大覆盖清单](trials/2026-10-22-coverage/coverage.json)；[Ubuntu 实验](trials/2026-10-23-ubuntu/README.md)。
- [Windows 安装来源](environment/install-provenance.md)、[固定源码](environment/source-revisions.json)、`environment/packages.json`、`environment/machine.json`；Linux 对应 `environment/ubuntu-2026-10-23/` 的 bootstrap、packages、requirements-lock、GPU、模型 hash 和 regression-tests。

### 报告当前存在的缺口

此次重新运行审计：仓库 `cases.json` 有 **89 个案例**，另有 6 个旧基线和 6 个阻塞项，预期 **101 张卡片**；HTML 缺少 `qwen-multiref-full-tail`。也不能用它覆盖10月21日“19条”的历史基线。

`trials/2026-10-22-coverage/coverage.json` 的 `queued`、Ubuntu `plan.json` 的 `running`、部分原始 summary 的 `running` 都可能停留在中断前。以具体执行记录、停止补记、history、实际文件为准。新审计保存在忽略目录 `runs/handoff-2026-10-24-audit.json`，可随时重新生成。

## 6. 已实现的代码与可用规避

### 6.1 可选辅助节点

- `code_source/gfx1032_quant_fallback/`：显式 `COMFY_GFX1032_INT8_FALLBACK=1` 时，绕过 gfx1032 上失败的 INT8 GEMM，走核心已有反量化/浮点计算；没有修复 AMD 原生 kernel，Linux 也不应不经对照默认启用。
- `code_source/cpu_chunked_logits/`：Qwen 输出层按词表行分块，默认最多 2048 行。原 CPU 临时申请 2,489,319,424 字节恰好是 `151936×4096×float32`。CPU/GPU 开关为 `BARELY_COMFY_CHUNKED_CPU_LOGITS=1` / `BARELY_COMFY_CHUNKED_GPU_LOGITS=1`；数值回归与完整 Linear 一致。它只降低这一层临时开销，不减少整个模型的常驻大小。
- `code_source/repair_conditioning/`：正负条件、Qwen 参考 latent、采样 latent 和 mask 的 safetensors 归档/读取，保留 dtype/数值，记录 SHA，限制路径、校验完整性、拒绝 NaN/Inf。包含 Save/LoadRepairConditioning、Save/LoadRepairLatent、SaveRepairQwenReferences、TextEncodeRepairQwenReferences。
- `feature_bench_ordering/` 只安排编码先后依赖，不拼接不同案例提示词。
- `gguf_unload_trace/` 是显式接入的卸载诊断；`gguf_mmap_offload/` 是候选规避，详见下面，二者均不是默认完成的修复。

### 6.2 attention 与工作流入口

- Kroma 的 FP16 split attention 曾生成全 NaN/Inf latent，API success 后解码黑图；`--force-upcast-attention` 的对照恢复有限值。黑图与正常图分别保留。
- 奇数查询长度使旧 split 公式退回整段，增加分片仍申请约 2.19GiB。补丁把切片宽度改成向上取整：`max(1, (q.shape[1] + steps - 1) // steps)`。见 [补丁](patches/comfyui-uneven-query-split.patch)及 `scripts/apply_split_attention_patch.py`；有备份、前后 SHA、未知源码拒绝、重复运行检查。
- `workflow_checks.py` / `replay_workflow.py` 提交前拒绝已知 MOSS 时间尺度错误与悬空引用。MOSS SFT 使用 AuraFlow、shift5，而不是错误的 SD3 multiplier。
- 同一提交返回有效 prompt_id 和部分 node_errors 时，重放器仍等有效输出，保留图片/history/校验错误，状态 `partial_output`，退出非零；不再因一个无效输出节点丢掉其他有效图。

### 6.3 三/四阶段隔离

- `run_conditioned_repair.py`：文本编码归档 → 退出 → 采样 latent 归档 → 退出 → CPU 解码。支持严格校验的 resume/条件复用、逐项采样/解码隔离。
- `run_qwen_reference_repair.py`：先单独 CPU VAE 生成参考归档并退出，再 GPU 文本编码时加载原值参考 latent，之后独立采样、独立 CPU 解码。真实参考归档已逐 dtype/逐值检查，不能改为手写 caption 或丢掉参考条件。
- `run_repair_batch.py`：自有服务、每案例独立证据、Windows commit 保护、`--unload-between` 走真实 `/free` 并等待 allocator 低于 256MiB。默认解释器仍是 Windows 路径，Linux 必须传 `--python-executable runtime/ubuntu/.venv/bin/python`；它的 `--min-commit-mib` 在非 Windows 返回 None，**不能当作 Linux RAM 保护**。
- CPU/GPU 模型切换、VAE 与大文本模型重叠常是峰值来源。单独进程可绕过这些路径，但不能据此关闭原生卸载问题。`--cache-none` 也没有解决所有跨案例内存压力。

## 8. 扩大排查与 native 卸载：最后进展及未验收候选

### Windows 已有实测

- **Z-Image**：同进程改变提示/seed 的 3+3+5 共11张均目视通过，文本编码和采样确实重跑；有/无预留2GB都通过，故“去掉 reserve-vram”不是已证实修复。旧第二张 `0xC0000005` 根因仍未结案。
- **Qwen 完整模型**：3轮采样 → 真实 `/free` → 重载通过；首次 allocator 从4,435,476,480降至67,108,864字节，后两次4,276,092,928降至67,108,864。见 `runs/qwen-full-reload-v1/summary.json` 及公开 `trials/2026-10-22-coverage/reloads/qwen-pinned/`。这是有限 latent/释放证据，不能自动说三张完整 PNG 或 OOM 清理通过。
- **Kroma 完整模型**：第一轮4步有限 latent 成功后，正常 `/free` 即 `GGMLTensor.to → Module._apply → unpatch_model` 原生退出；默认 pinned 和禁用 pinned 两组都失败，拒绝“关锁页就能修好”的假设。公开摘要在同目录 `kroma-pinned/`、`kroma-unpinned/`，raw 为 `runs/kroma-full-reload*-v1/`。
- 显式 trace 的最后失败参数是 `diffusion_model.txtmlp.3.weight`，GPU→CPU F32、6144²，约151MB。第二次 trace 观测 Windows commit 余量仅81,567,744字节，因此即使没有标准 OOM 文本，也不能声称卸载时内存充足。raw：`runs/kroma-unload-trace-v1/`、`v2/`。
- 候选 `RepairGgufMmapOffload` 在首次 GPU load 前保留独立 CPU base storage；让原 unpatch 去 LoRA/hooks/pins/backups但跳过整体 CPU 复制，再恢复原始存储。Kroma保留430个参数、5,958,640,944 raw bytes，未改权重文件或 Torch 核心。
- `runs/kroma-mmap-reload-v1/` 在 **禁用 pinned、FP16、attention upcast** 下完成3轮4步采样/真实 `/free`/重载，状态仍 `execution_pass_visual_review_pending`。每轮 `/free` 检查时 allocator 已约32MiB，不能把这些前后数值说成该次调用从数GB释放；只确认低于256MiB且继续执行。尚缺默认 pinned、LoRA 强度变化/恢复、完整 PNG 目视、更多模型、OOM/异常恢复和严格输出差异验证。
- 候选前后 latent 文件 SHA 不同，未证明逐张量或逐像素等价。小权重200轮保持hash也不能替代这些验收。**候选默认关闭，暂不可统一推广或宣布根因修复。**

### 功能广度与尚未跑完的配方

九个新增公开 case 中有 Turbo 角色/姿态/多参考及普通编码器对照、Kroma裁切换头/去狐狸参考、Qwen完整尾部。主要语义可生成，但精确人物身份仍不充分；同条件普通编码器也能做角色/姿态，单例未证明 UN 优势。六个 Turbo 四阶段案例的真实参考 latent 与原条件逐值一致。

待继续：BFS 前缀无LoRA / LoRA无前缀、768²四阶段；Kroma清空旧头 latent、`index` vs `index_timestep_zero`、8步和BFS LoRA、相同FP16的多参考消融；FLUX无额外字/20px蝴蝶结。`runs/breadth-queue-results.json`、`further-jobs-results.json` 只记录已执行部分，不表示所有队列完成。

BFS 的 Pruna 是作者文档中的**可选加速器**，缺它不构成继续验证的阻塞；旧15步GGUF仍不是作者int8+8步完整配方。Krea BFS LoRA 已下载并核对 LFS SHA（`abc6c468c578b36e6bd960106ad5886afd3f5321e4fe2de26c05bb5c6585b836`），但用于 Kroma OPD Q2_K 属实验兼容性测试。Krea插件只克隆在 `../amd_comfy/vendor/` 审阅，未安装；当前核心已有 `ref_latents`，不要因旧 README 再误判完全不支持参考。见 `research/kroma-bfs-compatibility-2026-10-22.json`。

## 9. Ubuntu 已做的工作和真正的停止位置

这批是共享盘上 **2026-10-23 Linux 实验**，不是计划中的空目录，也不是全新设备已验证。

- Ubuntu22.04.5 / kernel6.8.0-138、16GB RAM、无swap；独立 Linux Python3.12.14 环境在 `runtime/ubuntu/.venv`。系统Python3.10、Windows环境未替换。
- 固定 ComfyUI `ce1e922d8623bb507180e32a0c01a7d0e29edef7`，GGUF `373048b8403a7820620065210a691263d4da0a61`；从原本地 Git commit 导出，排除旧 Windows 工作区脏源码。
- torch2.12.0+rocm7.14.0、torchvision0.27.0+rocm7.14.0、ROCm7.14.0、原生 gfx1032；未设置 `HSA_OVERRIDE_GFX_VERSION`。FP32/FP16/BF16 GEMM、SDPA和最小GPU检查均有通过记录。原 Windows ROCm7.2/torch2.9.1初始化故障仍是独立历史问题。
- **Z-Image 同进程3/3完整出图、3/3目视通过**：红/蓝/绿壶，两颗柠檬，512²、9步、CFG1、Euler/simple、shift3，GPU文本、CPU VAE；文本和采样每次重跑。提交至history约300.97/102.35/40.20秒，冷启动和缓存状态不同，不能直接归因提速。
- GGUF真实Q4_K约8.3MB和INT8真实8MiB权重各200轮GPU→CPU/unpatch通过，包括交替人为Python异常后的显式清理；没有启用候选修复。小参数探针不模拟真实OOM、整模型或原生崩溃。
- 相同seed的 PyTorch attention 对照成功并目视通过，图与默认attention不逐像素相同，缓存/冷热状态未控制，不能宣称加速。该服务真实 `/free` 使allocator从6,415,187,968降至33,554,432字节，服务继续响应；仍不是异常/OOM恢复。
- 原有 **30项回归**通过（6工作流、1HTTP、11分阶段图、6归档、2attention、3参考阶段、1logits）。HTTP首次因沙箱不许socket失败，沙箱外重跑通过；attention受限预算测试里的OOM是预期对照，不能算新真实生图OOM。
- **Qwen pinned 首次完整加载没有完成**：十多分钟停在GGUF `pin_weight_to_device` 的GPU/CPU搬运后人工停止，未观察到native crash、OOM或RAM保护触发，没有图片或重载验收。停止时controller cleanup曾 `TimeoutExpired`，随后原记录确认controller/server退出。以 [结果补记](trials/2026-10-23-ubuntu/qwen-pinned-load-result.json)、[停止原因](trials/2026-10-23-ubuntu/qwen-pinned-load-operator-stop.json)、[栈](trials/2026-10-23-ubuntu/qwen-pinned-load-stack.txt)为准，不信raw summary遗留的running。
- 256MiB/1188MiB一般传输探针在已有3072MiB GPU驻留下通过，只能排除该一般搬运情形，并没有证明具体GGUF pin路径正常。
- **最新 CPU detach 回归还没进入被测行为**：`test_gguf_cpu_detach.py` 从权重找≤1MiB的Q4_K张量，`next(...)` 抛 `StopIteration`，见 `cpu-detach-test-before.txt`。因此没有有效“修复前行为失败”证据，也没有修复后通过；先换成存在且受控的真实fixture，再判断是否需要CPU-only mmap detach，保留GGML类型、形状、patch列表、bias/buffer及重复pin语义。

rocSHMEM 导入仍提示找不到 libnuma，系统已有 `libnuma.so.1`，但本轮计算通过；保留告警，不靠随意系统软链接掩盖。更完整证据在 [Ubuntu实验](trials/2026-10-23-ubuntu/README.md) 及同目录JSON；README尚未完整收录最后的Qwen停止/fixture失败，以上补齐。

## 10. Ubuntu 接着使用现有环境

先确认当前路径、设备权限和空闲资源；本次交接工具端检查的是 Windows 侧，不能据此宣布 Ubuntu 服务当前存活。旧 PID 和 localhost URL 都不代表现在的状态。

```bash
# 从共享的 MyProject/amd_comfy 进入实际代码仓库
cd ../comfyui-rx6650xt-lab
git status --short --branch
findmnt -T .
ls -l /dev/kfd /dev/dri/renderD*
free -h
ss -ltnp | grep -E ':(8188|8189|8190|8767)\b' || true
runtime/ubuntu/.venv/bin/python --version
```

先核对 `runtime/ubuntu/model-paths.yaml` 的绝对挂载位置是否仍有效；它不会随文档相对路径自动变化。Linux venv 的Python原路径也可能依赖先前的Codex runtime，若不可执行，再按固定版本重新建独立环境，不能改用Windows `.venv`。

上次 `/dev/kfd` 权限靠**临时ACL**获得，重启双系统后可能失效；必要时按09文档重新授予当前用户访问实际存在的设备。不要照搬历史用户名/设备编号。Codex沙箱也可能隐藏GPU：主机权限正确仍需在能访问设备的终端验证。

```bash
# 已有环境有效时，先检查，再启动。GPU检查会实际执行小运算。
runtime/ubuntu/.venv/bin/python scripts/check_gpu.py
bash scripts/start_ubuntu.sh
```

默认8188仅监听127.0.0.1，GPU编码/采样、CPU VAE、关动态显存和异步卸载、保持默认pinned；可用 `COMFY_RUNTIME` 指定独立runtime。不要从Windows FLUX锁页结论直接推导Linux最优设置。

如果现有Linux环境失效，再使用已有安装器（不是每次接手都重装）：

```bash
python3.12 scripts/setup_ubuntu.py \
  --source ../amd_comfy/ComfyUI \
  --models ../amd_comfy/ComfyUI/models
```

它需要Linux CPython3.12、现有模型和原ComfyUI/GGUF仓库中的固定Git对象；不会自动clone/寻找其他版本。缺少对象、旧轮子下架、设备不符时应记录失败再决定更新版本。安装器对已存在辅助节点目录不会覆盖更新，修改 `code_source/` 后须核对runtime副本，不能只改仓库就以为服务加载了新代码。先停止自己的服务、比较/备份后再同步所需节点。

连续Z-Image可沿用已验证入口，输出目录必须全新，先确保没有其他重任务：

```bash
runtime/ubuntu/.venv/bin/python scripts/repro_gguf_repeat.py \
  --runtime runtime/ubuntu \
  --workflow trials/2026-10-21-gguf-repeat/workflow.api.json \
  --model-paths runtime/ubuntu/model-paths.yaml \
  --out runs/ubuntu-zimage-next --count 3 --timeout 900 \
  --min-available-ram-mib 768
```

`trials/2026-10-23-ubuntu/run_qwen_reload.py` 包装了Linux物理RAM保护（1536MiB），并明确传Linux解释器；重跑前先解决/量测已记录的长加载路径，不要直接无限重复十多分钟等待。Z-Image的768MiB保护与Qwen的1536MiB不是同一个阈值；两者都不是完整OOM保证。

只看报告无需GPU，可在仓库根另开终端（先确认8767未占用）：

```bash
python3 -m http.server 8767 --bind 127.0.0.1
```

入口 `http://127.0.0.1:8767/trials/2026-10-19-features/feature-report.html`。8189曾用于H3隔离，8190用于自有诊断；服务端口不是案例完成状态。

## 11. 推荐下一步与各自完成条件

1. **先接住WIP与报告缺口**：确认Linux加载的runtime/模型/辅助节点正是当前版本；补 `qwen-multiref-full-tail` HTML卡片并保留全部旧评价。完成条件是索引、案例、图与history绑定一致，不能为了清零待办把partial改pass。
2. **定位Linux Qwen GGUF pin长加载**：先修CPU-detach测试fixture，做真正可解释的前后对照；再量测具体权重、mmap/pin/device转换。保持默认pinned基线；每个变化独立记录。完成条件是完整编码、采样、解码/目视，再验证同进程变提示重载和真实/free；一般大张量传输通过不代替模型链路。
3. **验证Windows Kroma CPU-backing候选的正确性**：默认pinned、LoRA加载/强度变化/卸载恢复、真实输出差异、多个完整模型、正常卸载与异常/OOM清理分别做。Linux如试候选，另建实验，不用Linux成功关闭Windows问题。通过前默认关闭。
4. **人物/动物身份与参考消融**：固定输入顺序、seed、模型/精度，拆BFS前缀和LoRA；Kroma `index`/`index_timestep_zero`、清旧头latent、8步兼容性分别测。验收包括五官/雀斑、头向、发型、衣领/背景污染、完整尾部，不能只看“像一个狐狸/红发人”。
5. **CPU反推和FLUX细节**：原Qwen8B CPU继续记未完成；Smol需改善重复和延迟、核对输入内容并自动接出图，另标替代模型。FLUX直接模型的额外文字和小蝴蝶结尺寸未过，后续尝试需拿到真实PNG；不能只记录4/4采样后解码保护停止。必要时拆采样/CPU tiled解码，保留原保护阈值，别单纯降低保护硬跑。
用户删除的标准ModelScope权重不自动恢复。H3目前仅384×256、5帧、4步诊断可执行，正常视频、角色替换、BFS、续写、长音频没有完整验收；124帧失败曾在其他任务并行时发生OpenBLAS分配失败，不能当资源隔离后的硬件上限。H3在最近修复任务中被排除优先级，保留待办即可。

每个新尝试：记录问题/假设 → 固定工作流与源版本 → 单变量对照 → 实际执行/资源 → 输入输出/目视 → 判断是否仅规避 → 剩余项。更新 `docs/08` 或新增Linux日记，并把原始文件保存在全新 `runs/<唯一名称>/`。

## 12. 继续验证与发布时的注意点

- 可先重跑无需GPU的 `test_workflow_checks.py`、`test_replay_partial.py`、`test_conditioned_graph.py`；需要Torch/核心源码的测试还有 `test_repair_conditioning.py`、`test_split_attention_precision.py --runtime runtime/ubuntu`、`test_qwen_reference_phases.py --runtime runtime/ubuntu`、`test_chunked_logits.py --runtime runtime/ubuntu`。30项通过是历史记录，本次交接没有重新执行GPU或完整回归。
- `python3 scripts/audit_feature_backlog.py --source . --out runs/backlog-next.json` 可重查漏卡与历史记录。它不是语义去重后的功能剩余数，也不会重新目视图片。
- 原始图片绑定检查工具在 `../amd_comfy/trials/2026-10-19-features/verify_outputs.py`，脚本中旧绝对路径在Ubuntu需要映射；公开PNG已去metadata，不能期待它仍含原prompt。公开副本与原图逐像素相同，但SHA不同；通过来源清单/history绑定追溯。
- `verify_publication.py` 检查语法、链接、敏感内容和图片metadata，`publication-manifest.json` 是发布快照。当前WIP会导致旧manifest不匹配；这不等于新模型实验失败。准备发布时先审核新增内容，再更新manifest/检查；不要用全量原目录覆盖精选快照。
- 本次交接检查的40个文档相对链接均存在，本文自身格式检查通过。整个既有工作区的 `git diff --check` 仍报告两份主报告的行尾空白/CRLF问题；`.gitattributes` 明确 `* -text` 以保留公开快照字节及hash，不要在双系统切换时全量自动换行转换。应在单独审核报告变更时处理，并同步相关manifest。
- 当前 `runs/queue-priority-pause.json` 的PID21572和 `resume_required` 是历史Windows队列记录，此次Windows进程检查未见该队列或ComfyUI/报告服务；不要在Ubuntu按旧PID恢复。旧任务JSON仍可读，用新路径/解释器重新组织明确待办。
- 另有旧Codex调度 `automation`，本次读到配置仍为ACTIVE、每天00:30、目标会话 `01a154a0-96d0-7a51-abeb-15db83195437`。它属于Windows侧Codex状态，不随共享代码自动成为Ubuntu会话；本次未更改调度，别因看见heartbeat就认为相关计算已完成。后续若保留自动续跑，先确认不会重复启动任务。
- 本文件只恢复开发上下文；没有替接手后的Ubuntu实时验证做保证。事实优先级：实际源码/模型hash/执行图与history/输出 > 结果补记与目视review > 日记 > 旧会话里的阶段性总结。

## 13. Ubuntu 2026-10-24 续接追加（保留以上历史）

已补齐 qwen-multiref-full-tail 卡片，101条卡片齐全，旧100张article内容逐字节保留；未将部分达到改成通过。Linux环境等版本迁到SSD，95个依赖版本一致；7份模型核对SHA后复用只读挂载GIAO的NVMe副本，旧环境和HDD配置保留。CPU-detach fixture已修正，未改GGUF实际pin回调测试明确失败，CPU-only副本通过，并已仅应用Linux runtime，备份和hash均保存。

SSD/NVMe未改代码基线仍在编码器加载时HTTP60秒超时；补丁后编码器可完成，但原默认FP32 casting整图触发1536MiB RAM保护。后续FP16、分阶段条件/latent归档、真实/free验证的实际结果见 [10月24日续接](docs/journal/2026-10-24-ubuntu-continuation.md) 和 [本轮实验](trials/2026-10-24-ubuntu/README.md)。已有raw summary遗留running用结果补记澄清，勿当服务活着。

运行前确认NVMe仍挂载、GPU临时ACL有效；两个旧Windows卸载问题及CPU-backing候选未由这些Linux实测结案。源码固定commit仍是导出基线，运行副本另有明确patch hash，不能仅凭commit误认完全未改。

## 14. Ubuntu 本轮收尾状态（2026-10-24 追加）

默认 ComfyUI 已启动于 http://127.0.0.1:8188/，浏览器主画布可见，HTML/GPU/9个所需节点验证通过；报告服务为127.0.0.1:8767。实际PID和检查时刻见 `trials/2026-10-24-ubuntu/service-liveness.json`，不要把这里的历史“已启动”替代下次实时检查。无开机自启，重启后GPU临时ACL及GIAO只读挂载仍需核对。

本轮GGUF CPU-detach副本下，Z-Image默认参数同进程红/蓝壶2/2执行和目视通过；文本/采样均重跑。Qwen已有完整15步蓝图首轮、独立新进程绿图，图像健康正常，眼光等精确提示仍部分达到。**同进程连续Qwen仍未通过**：CPU heap trim没有消除第二轮/free的RAM峰值；省略纯文本编码中未用VAE的契约验证通过，但实际卸载也触发1536MiB保护，不是根因修复，两个选项默认不启用。独立进程出图是明确规避，不称重启修复。

34项回归通过；CPU detach有效fixture的原实现失败和候选通过均保留；默认/active释放指标分开。报告补齐漏卡后101张卡片，另追加50案例的历史Windows输出图库，原101张article字节保留、review文件未改。95个依赖版本与10月23日一致，SSD/NVMe及补丁源码SHA见新环境快照。

完整结果、每组失败边界、图片/history/源码绑定及复跑命令见 [10月24日实验](trials/2026-10-24-ubuntu/README.md)、[结果索引](trials/2026-10-24-ubuntu/outcomes.json)、[续接日记](docs/journal/2026-10-24-ubuntu-continuation.md)。本轮没有改写Windows结论，没有把身份、LoRA、CPU8B、FLUX细节及Windows native故障关闭；原49条重复尝试审计仍保留。后续优先研究Qwen主机内存峰值，而不是无限重复同一大图或降低保护阈值。

## 15. Ubuntu 重启后续接追加（2026-10-24）

本轮已确认重启后原 GIAO 挂载点不存在、NVMe 分区布局已变化，故第 13/14 节的挂载与 PID 只是历史。本轮未挂载/修改/格式化 NVMe；项目盘恢复桌面挂载后，从原 HDD 校验复制四份 Qwen 模型到 Linux SSD，保留原文件。Linux model-paths 已先备份再更新，GPU 临时 ACL 已恢复，无永久用户组改动或开机自启。

Python 3.12.14 基础运行库复制到 `/home/user/.local/share/barely-comfy/python-3.12.14-20261024`，不再依赖 Codex 缓存；原缓存和 pyvenv.cfg 备份保留，二进制 SHA 与 95 个依赖版本一致。最终正常组在这次迁移后执行。

新增实例级 CLIP backing（默认不连接），保留原 CPU 存储、clone 策略、量化元数据和梯度标记。v4 将部分 CPU 卸载请求转为全量恢复，以避开另一路复制/锁页；没有修改 stock GGUF 全局类或旧 MODEL 候选。新增延后 VAE 的纯文本图依赖，仍使用原 core VAE 解码；参考图/未知输入拒绝套用。

同 SSD stock 对照仍在第二轮编码末端触发 1536MiB 保护；v3 三阶段同进程两图通过，省略编码中未用 VAE 后观测最低 RAM 2789.9MiB。普通整图早期组有保护/有限观察中断，记录全保留；不得把早期停顿说成已证明永久死锁。最终 v4+延后 VAE 普通整图，在观察组和无诊断钩子的独立 Python 正常组均连续两张 512×512、15 步通过。正常组 PID24347 已由 runner 正常停止，两轮 118.07/132.09 秒、最低观测 RAM2320.5MiB，两次真实 /free active 检查通过；reserved 缓存仍保留，不能称完整显存释放或 OOM 恢复。

当前服务已恢复为 Qwen 专用参数的 8188，报告仍为 8767。实时 PID/时刻、GPU、7 个节点与空队列见 `trials/2026-10-24-ubuntu-followup/service-liveness.json`，勿沿用正文历史 PID。Qwen 启动入口 `scripts/start_ubuntu_qwen.sh`；普通启动脚本默认不变。蓝/绿 API 图位于新试验目录，可通过当前前端工作流打开入口载入。

本轮 24 项测试通过（18 工作流+2 无参考 VAE 契约+4 GGUF GPU 探针）；完整与部分卸载原路径先红后绿证据均保留。最终两图健康，精确提示仍部分达到；纯文本无 LoRA 验证不能关闭 LoRA/身份/参考消融、异常、Windows native、CPU8B、FLUX 或视频待办。旧报告卡片、reviews/cases 与 10 月 24 日首轮文档未改。详见 [重启后日记](docs/journal/2026-10-24-ubuntu-reboot.md)、[本轮全部证据](trials/2026-10-24-ubuntu-followup/README.md) 与 [结果索引](trials/2026-10-24-ubuntu-followup/outcomes.json)。

## 16. 模型 / 功能 / 平台汇报及 WebUI 库（2026-10-24 追加）

未测平台不继承通过。原 Windows HTML/MD 完整归档到同目录 `feature-report.windows-20261024.*`，原 cases/reviews/baseline/blocked 与原主 Markdown 未改，SHA 校验通过。旧生成脚本 CLI 转到新布局，历史 helper 保留，旧脚本字节备份位于新 trial。

`workflows/` 提供 100 份独立 API 配方、99 份真实前端导出/重载后参数与连线一致的 UI JSON、12 份内容不变的输入图片和完整 zip。99 份已安装到当前 runtime `user/default/workflows/模型功能库/模型/功能/`，后端列表可见。历史分阶段配方明确标注没有在当前 Linux 整图验收；所有 Windows 评价和未闭环事项保留。

修正模型和功能归类：Base/Turbo 看扩散权重，不看 UN 编码器；MOSS 看实际 SFT INT8；文生图素材与真实风格转换、改色分别归组。输入复制为 hash 文件名，解决前端 LoadImage 的子目录选择问题；MOSS JSON 花括号在 UI 转义，实际 API 文本不变；批量等待屏障只去调度依赖，不改 conditioning。seed 控制 fixed。

本轮安装后 Qwen 蓝眼 UI JSON 经实际 app.queuePrompt 单次提交，114.325 秒完整输出，最低观测可用 RAM3365.3MiB，图像健康；眼光和彩窗细节部分达到。只换保存前缀分离证据，其余输入不变，不能据此升级其他 98 份图。9 项新回归检查、桌面/手机搜索筛选展开、所有本地链接、zip CRC 通过。8188 仍为 Qwen 专用配置，8767 仍服务本地报告。没有发布线上站点、更新 publication manifest 或关闭旧 Windows/身份/LoRA/CPU8B/FLUX/视频/OOM 待办。

详见 `docs/12-platform-report-workflow-library-2026-10-24.md`、`workflows/README.md`、`trials/2026-10-24-platform-report/`；库生成流程见 README，HTML 入口原地址不变。

## 17. Linux功能补图收尾（2026-10-25追加，保留以上历史）

已完成本轮模型/功能/平台补图：9系列47组169条证据，新增42张Linux实测图，40组已有Linux输出；21组至少有一条达到本例目标，其余质量与身份细节保持实际部分/未达标，不将有图等同全通过。Windows101条源评价、原MD与完整HTML/MD归档SHA不改；根README/本文件仅追加。

最终268份UI前端导入/导出/重载核对通过，184份安装并在后端列表可见；H3诊断缺节点的API继续受阻。新Linux整图未验收的不默认安装，阶段文件与精确归档可用；完整包包含文字/条件归档，轻量包需先生成归档。API/输入/RGB/文件/阶段/归档SHA和模型盘21份权重只读清单均有证据。

参考图GPU编码定位到正/负文本向量全NaN，FP16/BF16失败保留，偶发编码通过不称修复；CPU/BF16编码、结束进程、GPU采样已补完各可执行功能。8B CPU自回归约312秒停止前12token，因延迟主动中止；8B GPU/BF16+backing候选触发1536MiB保护。独立4B VLM现有FP8权重约36秒生成完整描述，经原文/SHA文本归档自动交给8B CPU编码约58秒，再由Base采样约80秒；三阶段各PID和实际图均保存，未升级原8B反推。

Kroma主体外参考裁图得到猫头鹰；FLUX中文结构指令得到单嘴单C把手茶壶，1024分块CPU解码真实PNG完成但额外文字未消除。MOSS较强重绘仍无明确水彩；换头/身份、尾部与接缝、蝴蝶结尺寸、LoRA消融按实际边界保留，不关闭旧Windows/native卸载/CPU8B/视频/OOM任务。

44项回归通过，42张新图逐张目视并校验绑定；WebUI实际排队Turbo采样图约54.6秒成功，最低RAM7079.8MiB。默认8188为Qwen FP16/upcast/split/关闭pinned配置，报告8767；实时状态见新trial/service-liveness.json，不跨重启复用PID。模型主路径为KEKE的comfyui-models-20261024，旧SSD副本未删；临时GPU ACL和只读挂载仍需在重启后核对，无fstab/开机自启改动。

详见[本轮说明](docs/journal/2026-10-25-linux-coverage.md)、[工作流指南](workflows/README.md)、[证据与恢复入口](trials/2026-10-24-linux-coverage/README.md)、acceptance.json与generated-images.audit.json。恢复可用run_linux_coverage.py --staged --pending-only --timeout 600；真实失败和操作性停止不会盲目重复，源图改变需用新案例ID。旧原始日志和队列脚本中的PID只属当时，不按历史PID恢复。没有远程发布、commit/PR或更新publication manifest。

## 2026-10-25 平台证据修订追加

当前范围8系列/41功能组/163证据，Linux40组有图。已按用户要求缩减本卡不可用模型内容，其余95条Windows评价、source_sha256、original_case与原HTML案例字节通过保留校验。新版不作操作系统速度排名；每组附条件对照和Linux问题的确认程度、尝试、规避及未完成工作。原始Linux失败没有被后续变体成功覆盖。见docs/14-report-evidence-audit-2026-10-25.md。

## 2026-10-26 报告阅读修订追加

报告默认收起重复记录，67条Linux记录补齐测试目的、改动和结果；63条近期记录按时间排列，4条较早记录注明登记顺序。状态统一为通过/部分达到/未达到/未出图/未测试，原Windows评价不改。本轮未新增推理。已应用Humanizer和Vercel界面指南。GitHub继续更新PR #1。

## 2026-10-26 范围整理与阅读优化

按用户要求移除不再保留的系列及其资料、占位条目和旧总览截图。当前7系列、40项功能、162条记录；95条Windows原评价和卡片不变。Linux当前21项通过、18项部分达到、1项未达到。按Humanizer和Vercel界面指南补充结果筛选、网址状态保存、键盘跳转和图片尺寸。268份UI/API及184份本机推荐工作流的模型参数不变，本轮未推理。下载包需随新索引发布；继续更新GitHub PR #1。
