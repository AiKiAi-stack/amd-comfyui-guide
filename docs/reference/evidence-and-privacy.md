# 证据结构与公开副本

`evidence/<日期模型>/cases/<case-id>/` 保存实际图、history、result 及重试。`cases.json` 定义目标，`reviews.json` 保存目视判断。整批图的输出节点映射用于区分各项，拆出的单项图不能冒充实际整批提交图。

本仓库是经过筛选的公开快照。原始运行环境、模型文件、虚拟环境、账号配置、原始服务日志、浏览器数据和文章全文没有上传。文章来源只保留自行撰写的核验笔记与公开链接；私人网盘、签名下载URL和本机用户名路径做替换。

PNG 删除 tEXt/iTXt/zTXt/eXIf 块，WebP 删除 EXIF/XMP；像素/动画帧不重绘。这样避免图片内隐藏工作流、路径等元数据漏发。工作流作为独立清理后的 JSON 保留。`publication-manifest.json` 记录公开文件校验和、图片原件/公开副本校验和、发布处理规则。

**历史 `output-audit.json` / `.verified.json` 中的图像 SHA 是本机原件的校验值。** 去元数据后的公开文件 SHA 会变化；不要用原 SHA 判定公开图片损坏。模型权重未改写，其模型 SHA 仍用于下载校验。历史 PNG 元数据绑定检查是原实验的一部分，公开 PNG 已去元数据，不能直接重跑旧 `verify_outputs.py` 当成公开副本验收。

公开仓库检查：`python scripts/verify_publication.py`。检查报告链接、JSON语法、文件大小、已知凭据模式、个人路径、图片元数据和发布文件 SHA；不是能识别一切秘密的保证。未来提交仍需人工查看素材和日志。

新增实验写入 `runs/`（gitignore），要发布时单独整理新 case，保留失败，明确标注脱敏与计时范围。
