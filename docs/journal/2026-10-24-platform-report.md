# 模型、功能与平台对照 / WebUI 工作流库（2026-10-24）

[打开新版 HTML](../../report/index.html)；本地入口仍为 `http://127.0.0.1:8767/report/index.html`。

页面按 **模型 → 功能 → Windows / Linux** 展示 9 个模型/权重系列、46 个功能分组、106 条执行或待办证据。左右平台各自展示输出、原评价、全部重试与失败记录，展开可看复现步骤、精确权重名、输入图片/顺序、提示词、seed、分辨率、步数及采样器。搜索和筛选可以只看两平台已有记录、Linux 待验证或有工作流的功能。

不同平台的提示词、编码器、精度及执行方式可能不同；这份报告对照功能证据，不是严格跨平台速度基准。实际未验证的平台显示“未验证”，不继承另一平台的通过结论。最新有图案例只是代表例，历史失败没有删除。

原报告完整归档为 [Windows HTML](../../evidence/2026-10-19-features/feature-report.windows-20261024.html) 和 [Windows Markdown](../../evidence/2026-10-19-features/feature-report.windows-20261024.md)，SHA256 与重排前逐字节相同。原 cases/reviews/baseline/blocked 和原主 Markdown 未修改；校验见 [保留证明](../../evidence/2026-10-24-platform-report/preservation-after.json)。旧生成脚本的命令行入口改为生成新布局，历史渲染函数及备份保留。

## 在 ComfyUI 使用

WebUI 左侧 **工作流 → 模型功能库 → 模型 → 功能**，刷新列表后选择案例。99 份真正的 WebUI JSON 已安装，后端工作流列表也能返回这 99 个路径。报告可下载单份 UI JSON，或 [完整工作流与输入包](https://github.com/AiKiAi-stack/amd-comfyui-guide/releases/download/model-feature-workflows-2026-10-26/model-feature-workflows.zip)。输入图片已补齐本机；跨环境的复制方法见 [库说明](../../workflows/README.md)。

4 份 Linux 已出图预设分别为 Qwen 蓝眼/绿眼提示和 Z-Image 红壶/蓝壶。Qwen 使用专用启动脚本 `scripts/start_ubuntu_qwen.sh`，Z-Image 历史验证使用通用 `scripts/start_ubuntu.sh`，报告明确区分。当前 8188 保持 Qwen 专用配置。

99 份 UI JSON 均由本机实际前端生成，再载入、导出，逐节点比较输入与连线；seed 生成后控制固定。Windows 历史配方导入通过不意味着 Linux 已执行，历史分阶段结果也不成为当前普通整图的成功证据。MOSS 的 JSON 布局提示对花括号作 UI 转义，实际导出的 API 文本保持不变；输入文件复制到根目录的 hash 文件名，避免 LoadImage 下拉框不包含子目录文件的警告；批量图仅抽取本案例的依赖，去掉不改变 conditioning 的等待屏障。

MOSS 按实际 SFT INT8 权重归类，原模型标签保留。Base 与 Turbo 按扩散权重区分；UN 编码器不会把 Base 结果归为 Turbo。纯文生图参考素材、改色、风格转换分别归组。

## 本轮复核

- [9 项回归检查](../../evidence/2026-10-24-platform-report/tests.txt)：历史字节和评价、模型/功能归类、平台边界、批量图抽取、可移植参数、输入内容、安装文件与 HTML 转义。
- [桌面/手机真实浏览器检查](../../evidence/2026-10-24-platform-report/report-browser-checks.json)：9 模型、46 功能、106 条记录、92 平台面板，搜索、筛选、展开、清除正常，手机无横向溢出。所有本地引用存在，zip CRC 正常。
- [实际 WebUI 队列回执](../../evidence/2026-10-24-platform-report/webui-queue-receipt.json)、[history](../../evidence/2026-10-24-platform-report/webui-history.json)、[执行/内存](../../evidence/2026-10-24-platform-report/webui-execution.json)、[图片与目视](../../evidence/2026-10-24-platform-report/webui-visual-review.json)。从已安装 Qwen 蓝眼 UI JSON 打开，经 `app.queuePrompt` 实际提交，114.325 秒完成 512×512 图片，最低观测可用 RAM 3365.3MiB；没有触发 1536MiB 保护。只改保存前缀以保留独立证据，其他参数与库中 API 一致，未缓存模型计算节点。图像健康，蓝眼发光及彩窗精确细节仍部分达到。

本次真实出图复核的是一份已验收 Linux 配方。LoRA、人物身份、参考消融、CPU8B、Windows native、FLUX 细节、异常/OOM 清理和视频待办没有由此结案。未更新发布快照 manifest，也未发布线上站点。
