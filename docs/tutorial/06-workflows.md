# 06 · 工作流库：下载、导入与复现

本仓库为 **7 个模型系列、40 项功能**提供 **268 份**经过真实前端导入/导出回环核对的 WebUI 工作流及对应 API，本机安装了其中 **184 份**推荐工作流。每项功能的实测结果、输入与判定见[功能报告](../../evidence/2026-10-19-features/feature-report.html)（也可直接看[在线报告](https://aikiai-stack.github.io/amd-comfyui-guide/)）。

工作流库本身的结构、维护命令和实现细节见 [workflows/README.md](../../workflows/README.md)；本页只讲怎么用。

## 在本机使用

打开 ComfyUI 左侧「工作流 → 模型功能库」，按模型和功能选择文件；也可以下载单份 UI JSON，通过「打开工作流」载入。

## 在其他机器使用

下载 Release 包，解压后把包内 `input` 目录的内容复制到目标 ComfyUI 的 `input`，再打开 `ui` 目录中的工作流。包内不含模型权重。

| 包 | 大小 | 内容 |
| --- | ---: | --- |
| [完整包](https://github.com/AiKiAi-stack/amd-comfyui-guide/releases/download/model-feature-workflows-2026-10-26/model-feature-workflows.zip) | 约 360 MiB | UI、API、输入图片，以及经过 SHA256 校验的编码/描述文件 |
| [轻量包](https://github.com/AiKiAi-stack/amd-comfyui-guide/releases/download/model-feature-workflows-2026-10-26/model-feature-workflows-light.zip) | 约 12 MiB | 只有 UI/API 工作流，需先运行编码步骤 |

输入文件统一使用 `ModelLibrary` 开头的名称；原路径映射、文件 SHA 和完整参数见 [catalog.json](../../workflows/catalog.json)。

## 复现一项功能

1. 按该功能说明准备模型与启动配置（见 [05-models](./05-models.md) 与 [07-troubleshooting](./07-troubleshooting.md)）。
2. 打开对应的 UI 工作流，或直接提交 API 文件；输入图片按文件名对应到 `LoadImage` 节点，目标/参考顺序保持原图。
3. **分阶段方案**：先按该项说明完成编码，再按指定配置重启服务运行出图。修改提示词、图片或参考顺序后必须重新编码，并更新出图节点里的文件路径与 SHA256。
4. 对照功能报告里的结果与判定：工作流能打开、实际出图、达到目标、长期稳定是四件事，不互相替代。

## 已验证的边界

- 268 份都通过真实前端回环核对；184 份安装在本机，其余可按需导入。
- 「导入通过」不等于「在本机实际执行通过」，更不等于「达到目标」；实际结论以[功能报告](../../evidence/2026-10-19-features/feature-report.html)和各 case 记录为准。
- 修改过的工作流请自行复测，不要用旧结果代替新结果；本仓库保留失败与部分达到的记录，它们同样是有用证据。
