# Ubuntu 重启后续接：独立环境与 Qwen 普通整图

2026-10-24 追加；保留之前所有 Windows 结论与 [首轮 Ubuntu 记录](2026-10-24-ubuntu-continuation.md)。

本轮完成独立 Linux Python 环境，并使指定的无 LoRA Qwen 纯文本普通整图在同一进程连续输出两张 512×512、15 步 PNG。两次真实 `/free` 的活跃显存检查通过。此前失败、有限观察中断和源码版本均另存，没有将旧失败改成成功。

## 当前使用入口

当前 Qwen 配置服务：http://127.0.0.1:8188/。启动命令为仓库根的 `bash scripts/start_ubuntu_qwen.sh`；通用 `start_ubuntu.sh` 保留原默认参数。Qwen 入口明确使用 FP16、upcast/split attention、CPU VAE、fast disk、1GiB VRAM 预留，并禁用 async/dynamic offload；默认 pinned memory 仍开启。

载入 [蓝色提示工作流](../../evidence/2026-10-24-ubuntu-followup/qwen-ubuntu-blue.api.json) 或 [绿色提示工作流](../../evidence/2026-10-24-ubuntu-followup/qwen-ubuntu-green.api.json)。两个文件就是最终实际执行的 API 图，当前前端支持通过工作流打开入口载入。图中显式启用实验节点，未连接节点的图不改变行为。

报告服务仍为 http://127.0.0.1:8767/report/index.html 。本轮没有修改原报告的 101 张卡片及 Windows reviews/cases。最新 PID、时刻、GPU、7 个所需节点及空队列检查见 [当前服务记录](../../evidence/2026-10-24-ubuntu-followup/service-liveness.json)。本轮没有新浏览器截图，不把 API 就绪说成浏览器目视验收。

## 改动及其原因

重启后 GPU 临时 ACL 丢失，本轮已恢复。项目 NTFS 盘仍存在；旧 GIAO 挂载点已不可用，NVMe 分区布局与之前不同。本轮没有修改、挂载或格式化 NVMe。四份 Qwen 权重从原 HDD 校验复制到 Linux SSD，并完整读回核对 SHA；Linux 模型路径先备份，再改为 SSD Qwen 优先、其余 HDD 回退。原模型和 Windows 环境保留。

venv 位于 `/home/user/.local/share/barely-comfy/ubuntu-20261024/.venv`。Python 3.12.14 的基础库另外复制到专用 SSD 目录，避免依赖 Codex 缓存生命周期。原解释器和 venv 配置备份保留，二进制 SHA 与 95 个依赖版本不变；标准库扩展、原生 GPU 检查及迁移后完整两轮出图通过。

保留上轮仅 Linux 的 CPU-detach 补丁。本轮新增实例级 CLIP backing 节点：加载前保留 CPU 原始存储，卸载时恢复该存储，避免重新申请全量 GPU→CPU 权重副本；clone 必须保留策略，梯度标记及量化元数据保留。部分 CPU 卸载请求在选中实例上执行完整恢复，牺牲部分驻留，避免另一路复制/锁页。stock 全局 GGUF 类和旧 MODEL 候选均未改。

新增延后 VAE 节点，仍调用原 core VAELoader，仅以采样 latent 为加载依赖。纯文本编码中未使用的可选 VAE 输入先移除；最终 CPU 解码仍使用原 VAE。参考图或未知输入不会套用这个图变换，以免引入循环依赖。两个 helper 均由 setup 的显式选项安装，候选在工作流中未连接时不启用。

## 实际验证

| 路径 | 结果 | 最低可用 RAM MiB |
| --- | --- | ---: |
| 同 SSD 路径 stock 三阶段 | 首图完成，第二轮编码末端触发保护 | 1425.4 |
| CLIP backing v3 三阶段 | 两图、六次 active 释放检查通过 | 1635.3 |
| v3 三阶段，编码省略未用 VAE | 两图、六次 active 释放检查通过 | 2789.9 |
| v4 + 延后 VAE 普通整图，观察钩子 | 两图、两次 active 释放检查通过 | 2822.5 |
| 独立 Python，同配置普通整图，无钩子 | 两图、两次 active 释放检查通过 | 2320.5 |

最后一组两轮分别 118.07/132.09 秒。保护线始终 1536MiB，没有禁用默认锁页内存、host trim 或新加 swap。所有组的完整参数、源码/执行图/history/原 PNG SHA 均保存在 [结果索引](../../evidence/2026-10-24-ubuntu-followup/outcomes.json)。24 项本轮测试通过：18 项工作流、2 项无参考 VAE 契约、4 项实际 GGUF GPU 卸载探针；原实现及候选早期失败也保留。

最终两张图片已目视，无黑图或明显坏块，主体、剑、教堂、雾和红月可辨认。眼部发光和破碎彩窗等精确细节仍部分达到。[完整图片、评价与复跑命令](../../evidence/2026-10-24-ubuntu-followup/README.md) 包含原图到去 metadata 副本的逐像素绑定。

## 结论边界及后续

active 显存检查允许 ROCm 保留分配器缓存，reserved 检查没有通过；不能宣称全部预留释放或 OOM 恢复。FP16 路径与默认 FP32 casting 不等价。候选与 stock 的编码条件也有小数值差异，没有宣称像素级等价。

普通整图的早期组出现长加载，曾按有限观察窗口中断；这不是永久死锁证明。后续观察组及不带钩子的正常组均完成。实际抓到的栈在正常采样反量化，不能用它确定先前长加载的根因。所有原始中断证据保留，长期稳定性不能由两轮概括。

当前通过仅覆盖指定无 LoRA、无参考图的纯文本图及正常卸载。LoRA/身份/参考消融、异常/OOM 清理、CPU 8B 反推、FLUX 精确细节、视频及 Windows native 卸载故障仍按原交接保留。不要用本轮 Linux 成功关闭这些问题，也不要恢复用户已删除的权重。

重启后仍需核对项目盘挂载与临时 GPU ACL；本轮没有设置开机自启。服务状态与 PID 应实时检查，不能沿用以前的文字记录。
