# Ubuntu 独立验证 · 2026-10-23

本轮重新建立 Linux 环境并继续检查连续出图和量化卸载。Windows 的成功、失败和未闭环记录均保留。本页只解释新的 Ubuntu 实测，不将重启进程称作卸载修复。

## 同一进程连续三张 Z-Image

**3/3 执行成功，3/3 目视通过。** 同一个 PID，依次改变颜色和 seed，正向文本编码节点 8 与采样节点 10 每次都重新执行，未命中相应缓存。两次后续请求都记录了扩散模型部分卸载和文本模型重新加载。结束后测试服务自行退出。

使用与历史试验 SHA 完全相同的双 Q4_K_M GGUF、AE VAE，512×512、9步、CFG1、Euler/simple、shift3；GPU 文本编码、CPU VAE、关闭动态显存/异步卸载、默认锁页内存。源码提交与 GPU 栈见 [环境记录](../../docs/09-ubuntu-setup-2026-10-23.md)。只在新副本应用已归档的奇数查询切片修复；没有启用 GGUF CPU backing 候选补丁。

| 次序 | 颜色 | 提交到 history | 目视结果 |
| --- | --- | --- | --- |
| 1 | 红 | 300.97 秒 | 正常红壶、两颗柠檬 |
| 2 | 蓝 | 102.35 秒 | 正常蓝壶、两颗柠檬 |
| 3 | 绿 | 40.20 秒 | 正常绿壶、两颗柠檬 |

第三张九步采样约31秒；总耗时含模型加载、编码、CPU VAE和轮询，不含服务冷启动。前两张较慢的原因没有单独隔离，不能只凭逐张加速就认定是某一个缓存或存储因素。当前模型位于 NTFS 数据盘。

[实际提交图、history 绑定和日志信号](zimage-repeat/summary.json)；[逐张目视记录](reviews.json)。公开 PNG 去除元数据，逐像素校验与原图一致，原图/公开副本 SHA 分开保存。完整日志和原始 history 位于本地 `runs/ubuntu-20261023-zimage-repeat-01`。

![Linux 连续第三张绿壶](zimage-repeat/repeat-03-green_00001_.png)

复跑（需要 GPU 设备权限，输出目录必须全新）：

```bash
runtime/ubuntu/.venv/bin/python scripts/repro_gguf_repeat.py \
  --runtime runtime/ubuntu \
  --workflow trials/2026-10-21-gguf-repeat/workflow.api.json \
  --model-paths runtime/ubuntu/model-paths.yaml \
  --out runs/ubuntu-zimage-new --count 3 --timeout 900 \
  --min-available-ram-mib 768
```

## 继承待办的当前核对

[新审计快照](backlog-audit.json)核对当前仓库101条预期卡片，发现 `qwen-multiref-full-tail` 缺少 HTML 卡片。脚本归类49条未闭环记录，其中包含同一功能的多次尝试，不能称作49个独立新功能，也不能拿它替换10月21日“19条”的历史基线。原报告和评价未被本轮覆盖。

原有30项回归通过：工作流检查6、HTTP部分输出1、分阶段图11、条件归档6、attention2、Qwen参考阶段3、分块logits1。HTTP测试第一次因沙箱禁止本机 socket 失败；原失败与沙箱外成功重跑都保存在[测试记录](../../environment/ubuntu-2026-10-23/regression-tests.json)。attention OOM 是受限预算测试的预期异常，不能当作本次真实生成的 OOM。

后续卸载诊断和 attention 对照按实际结果追加。

## 量化卸载诊断

真实 Q4_K 权重 8,294,400 字节，GGUF GPU→CPU/unpatch **200/200**，循环约1.47秒；真实 TensorWiseINT8Layout 权重8MiB，**200/200**，约1.48秒。普通清理与人为 Python 异常后的清理交替执行，每轮原始量化数据 SHA 不变，显式 cleanup 完成，两进程退出码均0。耗时不含 Python/依赖冷启动。

[GGUF结果](probe-gguf.json)、[INT8结果](probe-int8.json)。GGUF 的只读 NumPy mmap 警告原样保留，探针没有写入映射。没有启用 CPU backing 候选修复；小权重循环不模拟真实 OOM，也不证明完整 Qwen/Kroma 卸载已修好。

## attention 对照及真实释放

新进程加 `--use-pytorch-cross-attention`，重放第一张完全相同的工作流及 seed，执行和目视均通过，[实际输出与绑定](pytorch-attention/result.json)。输出与默认 attention 图并非逐像素相同。约200.74秒端到端、采样约38秒；文件/模型/kernel缓存状态没有独立控制，不宣称得到加速，默认启动脚本继续使用已连续验证的默认 attention。

随后对这个自有服务实际请求 `/free`：Torch GPU保留内存从6,415,187,968字节下降至33,554,432字节，约6.58秒，服务继续响应。[释放证据](zimage-explicit-unload.json)。这不是异常/OOM后的恢复测试。为了给Qwen保留RAM，之后正常终止该对照服务；Qwen结束后恢复默认8188界面。

[连续测试内存摘要](memory-summary.json)最低观测可用物理内存约2.15GiB，没有触发768MiB保护；进程RSS包含mmap文件页，不能与Windows commit直接比较。
