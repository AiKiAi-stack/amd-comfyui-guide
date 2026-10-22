# 2026-10-22 排障证据

[完整解决过程](../../docs/08-repair-journal-2026-10-22.md)按E01—E06保留实际尝试。

- [量化卸载小参数探针](bounded-probes.json)：两路各200次，初次和显式清理后复跑；不证明完整模型崩溃根因修复。
- [相同FP16的CFG控制](cfg-control.json)：实际采样图仅CFG不同，身份仍部分达到。
- [资源观测](memory-comparison.json)：保护停止、主动停止与四阶段成功分开；GPU峰值未采样。
- [29项回归及1个预期失败对照](verification.json)。
- attempts/保留三次无PNG失败的实际执行图与日志SHA。最终图片与数值证明在[修复案例](../2026-10-21-repairs/README.md)。
