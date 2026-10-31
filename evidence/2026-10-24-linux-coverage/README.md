# 模型迁移后的 Ubuntu 功能补图

这轮从 2026-10-24 开始，继续完成跨平台报告与工作流库。Windows 原评价和原图不改；Linux 每个实际尝试单独保留 API、提交回执、history、停止边界、输出图片与目视评价。

[实时汇报](../../report/index.html) 按模型 / 功能并列两个平台。Linux 进度分为“已有输出图片”“已尝试无图”“尚未执行”；有图仍须分别判断功能是否达到。没有图片的实际停止会保留，不用 Windows 输出填充 Linux。

模型盘 KEKE 重新以只读挂载，运行配置引用 `AIModels/amd_comfy/comfyui-models-20261024`，必要资源从既有 repair、zimage、flux2 子目录补充。四份原根分区 Qwen 副本没有删除；本轮运行优先使用 KEKE，不重新下载或复制模型权重。[当前路径](model-paths.yaml)、[只读 SHA256 清单](migrated-models.json)。

计划文件 [plan.json](plan.json) 列出功能案例和实际 Linux 配方变化，包含新 GGUF 文本编码器变体与保留的原编码器内存保护停止。`cases/<案例>/execution.json` 是最近有效结果，`review.json` 是实际目视评价；旧控制器错误、整图停止及映射配置对照保留为带后缀的 JSON。`cases/<案例>--encode/` 与 `--sample/` 保存分阶段 API 和各自 history；采样使用的归档 SHA256、先编码进程结束后再采样的记录写在主结果中。

每次服务只属于本次验证，端口 8190；以 1536MiB 可用物理 RAM 为停止边界。保护停止记为 operator stop，不冒充 native OOM。Kroma 整图在模型加载段有限观察未出图，单独关闭 pinned / mmap 选项没有消除停顿；分进程方式已有完整输出。小权重 mmap / CPU-copy 两组传输都通过，不能将小权重测试当成完整模型链路修复。原始停顿和诊断日志保存在 `runs/linux-coverage-20261024/`。

FLUX 标准文本权重在整图与单独编码阶段触发 RAM 保护；新增 Linux 变体用现有 `Qwen3-4B-Q4_K_M.gguf` 替代 `qwen_3_4b.safetensors`，FLUX.2 扩散权重、提示词与采样参数保留。GGUF 变体也分别记录普通整图与分阶段结果，不算原编码器配方通过。

分阶段图片不证明整图、同进程重载、真实 `/free` 或异常/OOM 清理已修复。库内整图标注配方状态，并补充可载入的编码 / 采样阶段文件与对应归档。修改提示词或输入后要重新编码，并在采样图中更新文件和 SHA256。平台结论以实际执行模式为准。

早期恢复入口（保留历史；当前恢复请使用下方“最新恢复命令”的 pending-only 方式）：

```bash
runtime/ubuntu/.venv/bin/python scripts/run_linux_coverage.py --auto --timeout 300
```

可用 `--models kroma` 或 `--cases 案例ID` 缩小范围；`--staged` 显式执行编码与采样两个进程。先确认常用 WebUI 没有用户任务，不能并行占用同一块 GPU。临时服务退出后恢复所需常用启动配置，再做前端回环、安装与下载包检查。

本轮完整验收和剩余阻塞以最终汇总为准。Windows 既有身份、LoRA、CPU8B、FLUX 细节与 native 卸载待办不由本轮 Linux 输出结案。

## 2026-10-25 CPU 编码规避与恢复入口（追加）

Qwen GPU 参考图编码的最小诊断已定位到正/负文本向量全 NaN，不是检查器误拦正常遮罩。BF16 单变量仍有失败，诊断组有一次通过，均保留。新 `cpu-encode` 案例采用 CPU/BF16 编码并结束进程，再启动 GPU 采样；归档有限数和 SHA256 检查保持严格。编码/采样的实际参数分别写入记录、UI 说明和汇报，不宣称 GPU 根因已修复。

最新恢复命令：

```bash
runtime/ubuntu/.venv/bin/python scripts/run_linux_coverage.py --staged --pending-only --timeout 600
```

只续跑未产生结果的有效案例或控制器错误；已成功、已确认失败和操作性保护停止不会被重新尝试。计划中 superseded 的旧配方仍保留，恢复时跳过。记录写入使用临时文件后替换，避免报告读取半份结果。运行前停止其他使用 GPU 的队列，核对项目/模型盘挂载与 GPU 访问；本文和旧恢复脚本中的 PID 都是历史，不能跨重启复用。

前端导入检查曾在只运行 CPU、未排队模型的8189临时服务上进行，实际模型执行服务仍为8190。前端通过与出图状态分别保存。第一次更新的完整/轻量包、导入和安装回执保存为 `*.progress-20261025.json`，收尾会再次同步全部新结果。

## 最终产出（2026-10-25）

新增42张Linux实测图片，40/47功能组有Linux输出；21组至少有一条达到本例目标，其余有图组保留部分达到/未达标。报告共9系列169条证据，Windows101条原评价和归档字节保持。

268份UI前端回环通过，184份已安装并在后端可见；H3诊断缺节点的1份API受阻。完整包约360.1MiB，轻量包约11.7MiB，CRC通过。44项回归及桌面/手机检查通过；从真实WebUI排队一张Turbo采样图成功。默认8188与报告8767已恢复，临时8189/8190已停止。

- [汇总及逐模型覆盖](acceptance.json)
- [图片、阶段和归档绑定](generated-images.audit.json)
- [原Windows文件与根文档保留证明](preservation-after.json)
- [最终测试](tests-final.json)
- [实际WebUI排队与安装文件绑定](webui-acceptance.json)
- [实时服务、空队列与184份可见文件](service-liveness.json)
- [报告链接检查](report-links.json)
- [完整说明](../../docs/journal/2026-10-25-linux-coverage.md)

4B辅助反推三阶段已完整执行：模型生成原文→SHA文本归档→8B CPU编码→条件归档→Base GPU出图。CPU原8B反推的延迟停止、GPU8B保护停止、参考编码NaN与所有历史部分达到均保留，未借辅助方案结案。归档不包含模型权重；修改输入或提示词须按案例的两阶段/三阶段步骤重新生成归档。
