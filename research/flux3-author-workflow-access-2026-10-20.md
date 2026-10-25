# Compshare 作者镜像页：公开工作流可获取性检查

检查日期：2026-10-20（Asia/Shanghai）  
公开页面：[Flux.3-5.6B-UN 一键部署](https://www.compshare.cn/images/uc0UnUzrIbtD)

## 结论

在该公开页面及其三个截图链接中，没有找到可直接下载的 ComfyUI workflow、API workflow JSON、节点图附件或内嵌 prompt/workflow 元数据。页面介绍给出的使用方式是启动镜像、查看 `/root/wan/log.txt`，然后点击 **SD-WEBUI** 按钮输入提示词并生成；它没有提供工作流导出入口。

这只能说明公开页面没有暴露工作流下载，不能据此判断 150 GB 镜像实例内部是否存有 workflow 文件。页面上的“使用该镜像创建实例”入口未点击；本次没有创建实例、注册或登录、租用 GPU 或付费。

## 检查到的公开内容

- 页面标题为“Flux.3-5.6B-UN”，版本 v1.0，最近更新日期为 2026-10-18；页面标注镜像大小 150 GB，并宣传 4 步、8 GB 显存、文生图、图像编辑、图生图、自动提示词和批量任务。
- “镜像介绍”只有两步：等待服务启动（约 2 分钟），可用 `tail -50f /root/wan/log.txt` 查看日志；随后点击 SD-WEBUI 按钮、输入提示词并生成。
- 可见运行环境写有 CUDA-13.2、JupyterLab:8888 和支持卡型；可见主要操作按钮是“使用该镜像创建实例”。页面文本搜索 `workflow`、`api.json`、`ComfyUI` 和 `json` 均未发现匹配内容。
- 页面“文生图”“图像编辑”“图生图”三节各有一张 PNG 截图。截图显示提示词、图像尺寸、迭代次数及生成结果等 SD-WEBUI 控件，没有 ComfyUI 节点图或工作流下载按钮。截图中出现 `work/config.json`（尺寸默认值说明）及 `ComfyUI/models/loras`（LoRA 目录说明）字样；这些只是界面文字，不能证明存在可下载 workflow。
- 检查三张 PNG 的标准文本块时，没有 `tEXt`、`zTXt` 或 `iTXt`；未发现 ComfyUI 常见的 prompt/workflow 文本元数据。

## 已保存的公开截图

文件位于 `trials/2026-10-20-flux3/author-assets/`。以下 SHA-256 对应下载后的本地 PNG：

- 文生图：[本地截图](../trials/2026-10-20-flux3/author-assets/screenshot-text-to-image.png)，2535×1814，2,053,203 字节；[页面原图](https://ucompshare-picture.s3-cn-wlcb.s3stor.compshare.cn/YBHH0yEIyAGA4Pd0%2F1792330838208.png)，SHA-256 `89322E077A678F5811EADC35D3219B10A54C63588CF896EC742D067CC2B3DF71`。
- 图像编辑：[本地截图](../trials/2026-10-20-flux3/author-assets/screenshot-image-edit.png)，3119×1872，2,204,076 字节；[页面原图](https://ucompshare-picture.s3-cn-wlcb.s3stor.compshare.cn/YBHH0yEIyAGA4Pd0%2F1792330850526.png)，SHA-256 `E86EB25B41BDA92434C6498B80567767BBB517A7181381718C3D367C03EB1E6C`。
- 图生图：[本地截图](../trials/2026-10-20-flux3/author-assets/screenshot-image-to-image.png)，3320×1881，2,415,394 字节；[页面原图](https://ucompshare-picture.s3-cn-wlcb.s3stor.compshare.cn/YBHH0yEIyAGA4Pd0%2F1792330863803.png)，SHA-256 `DF98D9F8EB7CE35280F14C347C658E19F5F668EBC34E06441588EA7B6CE18348`。

## 检查边界

本检查覆盖公开镜像详情页的可读正文、页面可见 UI、页面列出的三个截图链接及下载 PNG 的标准文本元数据。不包含实例内部文件、登录后控制台、作者未链接的存储对象或镜像本体；因此不能判断这些未公开入口中是否另有 workflow。
