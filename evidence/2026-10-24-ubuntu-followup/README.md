# Ubuntu 2026-10-24 重启后续接

最新验收：独立 Python、无诊断钩子的普通整图已连续完成两张；结果与可载入工作流见文末“最终普通整图验收”。

本目录追加 Linux 证据；之前的 Windows 评价、101 张报告卡片及 10 月 24 日首轮结果均保留。固定源码和模型与上一轮相同，实际补丁版本由每组 summary 的启动 SHA 区分。

## 已完成的分阶段对照

512×512、15 步、FP16 + upcast attention、默认 pinned memory、CPU VAE、同一 PID、每阶段真实 `/free`，物理 RAM 保护始终 1536MiB。没有启用 heap trim 或禁用锁页内存。

| 路径 | 两轮结果 | 最低可用 RAM MiB |
| --- | --- | ---: |
| stock，纯编码/free | 2/2，无出图声明 | 1937.4 |
| CPU backing v3，纯编码/free | 2/2，无出图声明 | 2032.4 |
| stock，完整编码/采样/解码 | 首图完成；第二轮编码末端保护停止 | 1425.4 |
| CPU backing v3，完整三阶段 | 两张 PNG、六次 active 释放检查通过 | 1635.3 |
| CPU backing v3，编码阶段省略未用 VAE | 两张 PNG、六次 active 释放检查通过 | 2789.9 |

同路径 stock 对照仍失败，不能把通过归因于 SSD 迁移本身。两轮纯编码都通过，也不能用它替代完整模型切换链路。

`active <=256MiB` 允许 ROCm 分配器保留缓存。这些组的 reserved 检查未通过，不能声称显存预留全部释放或 OOM 恢复。完整链路原始结果、PID、history/source SHA、RSS 与内存下界见 [phase-results.json](phase-results.json)。原始 `runs/ubuntu-20261024b-*` 保留，不回写其 pending 目视字段；公开副本单独附目视评价。

### 完整图片与评价

图像健康通过；蓝/绿眼部发光、破碎彩窗等精确提示细节仍只部分达到。没有修改既有 Windows 功能评分。

| CPU backing v3 | 省略编码阶段未用 VAE |
| --- | --- |
| ![蓝色提示](clip-full-blue/7-0-reload-01-blue_00001_.png) | ![蓝色提示](clip-no-vae-blue/7-0-reload-01-blue_00001_.png) |
| ![绿色提示](clip-full-green/7-0-reload-02-green_00001_.png) | ![绿色提示](clip-no-vae-green/7-0-reload-02-green_00001_.png) |

每个图片目录包含实际编码、采样、解码图及原图/history 绑定，PNG 去 metadata 后逐像素一致。候选与 stock 的编码张量不是逐字节等价：正/负条件有限，平均绝对差约 2.6e-5 至 6.1e-5，最大绝对差约 0.0089；初始 latent 完全相同。见 [conditioning-byte-comparison.json](conditioning-byte-comparison.json)。没有据此断言所有差异均由 backing 或某个分配器操作造成。

## 候选和失败探针

- `clip-cpu-backing-baseline.txt`、`clip-cpu-backing-baseline-final.txt`：实际 GGUF 完整 unpatch 遇到禁止新增 GPU→CPU 权重复制时失败，保留真实调用栈；这是分配路径探针，不是用 2MiB fixture 声称复现整模型 OOM。
- `clip-cpu-backing-candidate.txt`：初版暴露 clone 丢失策略；`candidate-02` 修正后通过。
- 首两组整编码失败分别是 core 默认 `manual_cast_dtype=float32` 被误拒绝、浮点参数默认梯度标记被误拒绝。原始运行和 v1/v2 源码保留；修正仅放行 core 标准计算策略，并保留原梯度标记。
- `clip-cpu-backing-float-grad-red.txt` 与 `candidate-04`：同一浮点参数模式先失败再通过。
- `clip-cpu-backing-candidate-final.txt`：3 项通过，包括 inference tensor 在 `/free` 的上下文之外复用 CPU 存储、晚加 LoRA 在 load 前被拒绝。
- `clip-partial-unload-red.txt`：完整卸载 v3 不能覆盖 core 的部分卸载路径，实际 `partially_unload → Module.to(cpu)` 再次触发复制断言。
- `clip-cpu-backing-v4-tests.txt`：4 项通过。v4 对部分 CPU 卸载请求执行完整恢复，放弃部分驻留；不修改全局 GGUF 类或旧 MODEL 候选。

LoRA、hooks、权重包装及其他 object patches 均拒绝。仅允许已核对的 core CLIP FP32 计算策略。CPU 存储生命周期、clone/weakref 根、inference tensor 包装均有独立约束。小测试通过不能代替整模型验证。

## 普通整图的补充诊断

v3 普通整图在模型切换时触发 RAM 保护；延后 VAE 加载后，仍进入另一个部分 CPU 卸载/重新锁页路径。v4 修正该部分卸载入口后，第一张普通整图与 `/free` 完成，但第二轮主模型加载久等，操作员停止并保留记录。`deferred-direct-01/02-operator-stop.json` 描述停止原因，原始 summary 的空 error 是 KeyboardInterrupt，不是自然成功或 OOM。

延后 VAE 节点调用原 core VAELoader，仅增加 LATENT 就绪依赖。它只适用于已确认不使用 VAE 的纯文本编码；参考图和未知参数形式会被 runner 拒绝，避免循环依赖。相关 runner 是独立诊断副本，旧 phase runner 原字节保留。后续带调用栈观察的结果另行追加，不把一张图等同于两轮通过。

## 本次重启与模型路径

系统盘/项目盘当前状态见 [environment-after-reboot.json](environment-after-reboot.json)。项目盘 `/dev/sda3` 已由桌面挂载为 NTFS3；GPU 临时 ACL 已恢复，原生 gfx1032 检查通过。无 swap，未改永久用户组、分区或 Windows 文件。

旧 GIAO 挂载点本次不存在，NVMe 分区布局已变化，不能继续沿用先前只读 NVMe 的当前态结论。本次没有挂载、格式化或修复 NVMe。从原 HDD 模型只复制 Qwen 四份权重到 Linux SSD，源文件保留，记录见 [ssd-qwen-models.json](ssd-qwen-models.json)。Linux 模型路径已备份为 [model-paths.before-ssd.yaml](model-paths.before-ssd.yaml)，新路径见 [model-paths.after-ssd.yaml](model-paths.after-ssd.yaml)，其他模型保留 HDD 回退。

## 复跑已验证的分阶段路径

在仓库根运行，下列输出目录必须不存在，8190 不得有其他服务。该脚本自建并停止服务，默认不开启两个实验选项：

```bash
runtime/ubuntu/.venv/bin/python trials/2026-10-24-ubuntu-followup/run_qwen_cpu_backing.py \
  --out runs/qwen-linux-next --free-check active \
  --clip-cpu-backing --omit-unused-vae \
  --workflow trials/2026-10-24-ubuntu-followup/clip-no-vae-blue/workflow.api.json \
             trials/2026-10-24-ubuntu-followup/clip-no-vae-green/workflow.api.json
```

Linux setup 新增显式 `--gguf-clip-cpu-backing`、`--deferred-vae` 安装选项，节点在图中未连接时不改变行为。`scripts/start_ubuntu_qwen.sh` 使用上述 Qwen 精度/attention 参数；通用启动入口不改默认值。服务启动本身不代表任意整图或其他模型已验证。

此次重新运行 18 项工作流回归、2 项无参考 VAE 契约、v4 的 4 项真实 GGUF GPU 探针均通过，合计 24 项。先前 34 项结果仍是先前记录，没有冒称本次全部重跑。

## 最终普通整图验收

v4 完整 CPU 恢复策略配合延后 VAE 的纯文本整图，完成了以下两组：

| 组别 | 同 PID 两张整图 | 每轮真实 /free 的 active 检查 | 最低可用 RAM MiB | 每轮总秒数 |
| --- | --- | --- | ---: | --- |
| 仅带 faulthandler 观察钩子 | 2/2 | 2/2 | 2822.5 | 115.08 / 111.05 |
| 独立 Python，无诊断钩子 | 2/2 | 2/2 | 2320.5 | 118.07 / 132.09 |

两组 reserved 检查仍为 0/2。精度仍为 FP16 + upcast attention，与默认 FP32 casting 不等价；默认 pinned memory 保持开启，没有 host trim、swap 或降低 RAM 保护线。源文件 SHA、PID、模型路径、每轮 API/history/原 PNG SHA 见 [outcomes.json](outcomes.json)，最终正常组为 `ubuntu-20261024b-qwen-independent-direct-01`。

前两组 operator-stop 只表示有限观察窗口内没有采样进展，不证明永久死锁。早期停止说明中的“120秒”是粗略观察描述，没有逐节点计时，不应当成精确模型加载延迟。后续观察组正常完成；实际抓到的调用栈位于第一轮正常 Q5_K 反量化/采样，不能据此为之前长加载给出确定根因。原始中断记录和失败结果均保留。

这不是修改全局 GGUF 卸载；部分卸载在所选 CLIP 实例上改为全量 CPU 恢复，会牺牲部分驻留策略。最终通过限于本组无 LoRA、无参考图的文本出图及正常卸载。身份、参考消融、LoRA 强度变化、异常/OOM 清理与 Windows native 问题仍未结案。

### 使用普通工作流

Qwen 专用入口：在仓库根运行 `bash scripts/start_ubuntu_qwen.sh`，服务为 http://127.0.0.1:8188/。当前已启动，具体 PID 与时刻见 [service-liveness.json](service-liveness.json)，不把此处文字当下次开机的服务状态。

通过 ComfyUI 的打开工作流入口载入 [蓝色提示 API 工作流](qwen-ubuntu-blue.api.json) 或 [绿色提示 API 工作流](qwen-ubuntu-green.api.json)。它们逐字节来自最终实际执行图，包含显式 CLIP backing 和延后 VAE 节点；普通启动入口与未连接这些节点的图不自动启用候选。已核对当前前端 `loadApiJson` 支持字符串节点 ID。没有新做浏览器截图；当前就绪检查为 HTTP/API/GPU/节点/空队列。

| 最终普通整图：蓝色提示 | 最终普通整图：绿色提示 |
| --- | --- |
| ![正常整图蓝图](direct-blue/7-0-reload-01-blue_00001_.png) | ![正常整图绿图](direct-green/7-0-reload-02-green_00001_.png) |

两图均目视健康；精确提示符合度仍为部分达到，见各目录的独立 review/result。这里没有回写原始 raw summary 的 pending 字段。

### 独立解释器与读回校验

Python 3.12.14 的基础运行库已复制到 `/home/user/.local/share/barely-comfy/python-3.12.14-20261024`，保留原 Codex 缓存副本；只更新 Linux venv 的 `pyvenv.cfg`，原 cfg 已备份。解释器二进制 SHA 一致，SSL/SQLite/lzma/bz2/zlib 可用，95 个依赖版本一致，venv 的搜索路径不再依赖 Codex 缓存；详见 [independent-python.json](independent-python.json)。最终正常两轮整图是在迁移之后执行，原生 GPU 检查也通过。

四份 SSD Qwen 模型均另行完整读回核对 SHA，见 [ssd-qwen-readback.json](ssd-qwen-readback.json)。这与复制时校验源数据的记录分开保存。没有改 NVMe 分区或原 HDD/Windows 模型。
