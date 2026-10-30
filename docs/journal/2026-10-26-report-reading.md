# 2026-10-26 报告阅读方式修订

同一标题下的Linux记录原来按新到旧排列，成功方案在前、早先失败在后，容易被理解为成功后又失败。本版默认只显示当前结果和图片，测试过程收起。

展开后按先后列出方案名称、测试目的、改动与结果。63条本轮Linux记录都有开始时间依据；4条较早的连续生成记录保留登记顺序，并注明缺少完整时间。67条Linux记录均补充了测试原因，没有新增推理任务。

例如橘猫改白猫先遇到GPU编码NaN，再改CPU/BF16出图；Turbo文生图先因内存保护停止，再减少额外CPU副本后出图；多图合成分别尝试GPU/FP16、GPU/BF16和CPU编码。不同配置的结果不能合成“同配置第几次稳定性测试”。

页面状态统一为“通过、部分达到、未达到、未出图、未测试”。Windows原评价、图片和参数继续保留在原始记录中。当前摘要用短句说明实现了什么、还缺什么；详细配置、错误和长评价放在折叠区域。默认可见文字减少约63%，见[浏览器检查](../../trials/2026-10-26-report-edit/browser-checks.json)。

采用了GitHub上的[Humanizer](https://github.com/blader/humanizer)精简冗余措辞，以及[Vercel Web Design Guidelines](https://github.com/vercel-labs/agent-skills/tree/main/skills/web-design-guidelines)检查标签、层级、键盘焦点和窄屏布局。两项技能已安装，本轮直接阅读其规则后应用。

本轮没有用标准Klein替代该版本，也没有把查找文件记成推理测试。
