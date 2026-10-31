# 06 · 工作流库：下载、导入、复现

工作流库覆盖 7 个模型系列、40 项功能，一共 268 份 WebUI 工作流，每份都经过真实前端导入导出的回环核对，并配有对应的 API 文件。这台机器上装了其中 184 份推荐工作流。每项功能的实测结果、输入和判定在[功能报告](../../report/index.html)里，也可以直接看[在线报告](https://aikiai-stack.github.io/amd-comfyui-guide/)。

工作流库本身的结构、维护命令和实现细节在 [workflows/README.md](../../workflows/README.md)，这一页只讲怎么用。

## 在本机用

打开 ComfyUI 左侧的「工作流 → 模型功能库」，按模型和功能挑文件。也可以下载单份 UI JSON，通过「打开工作流」载入。

## 在其他机器用

下载 Release 包，解压后把包内 `input` 目录里的内容复制到目标 ComfyUI 的 `input`，再打开 `ui` 目录里的工作流。包里不含模型权重。

| 包 | 大小 | 内容 |
| --- | ---: | --- |
| [完整包](https://github.com/AiKiAi-stack/amd-comfyui-guide/releases/download/model-feature-workflows-2026-10-26/model-feature-workflows.zip) | 约 360 MiB | UI、API、输入图片，以及经过 SHA256 校验的编码/描述文件 |
| [轻量包](https://github.com/AiKiAi-stack/amd-comfyui-guide/releases/download/model-feature-workflows-2026-10-26/model-feature-workflows-light.zip) | 约 12 MiB | 只有 UI/API 工作流，需先运行编码步骤 |

输入文件统一用 `ModelLibrary` 开头的名字。原路径映射、文件 SHA 和完整参数在 [catalog.json](../../workflows/catalog.json) 里。

## 复现一项功能

1. 按该功能的说明准备好模型和启动配置，见 [模型选择](./05-models.md) 和 [排障](./07-troubleshooting.md)。
2. 打开对应的 UI 工作流，或者直接提交 API 文件。输入图片按文件名对应到 `LoadImage` 节点，目标和参考的顺序保持原样。
3. 如果这项功能是分阶段方案：先按说明完成编码，再按指定配置重启服务、运行出图。改动提示词、图片或参考顺序之后必须重新编码，并更新出图节点里的文件路径和 SHA256。
4. 对着功能报告里的结果和判定看：工作流能打开、实际能出图、达到功能目标、长期稳定，这是四件事，互相不能顶替。

## 现有记录的边界

- 268 份都通过了真实前端回环核对。184 份装在这台机器上，其余按需导入。
- 「导入通过」不等于「在本机实际执行通过」，更不等于「达到目标」。实际结论以[功能报告](../../report/index.html)和各 case 的记录为准。
- 改过的工作流请自己重测，别用旧结果代替新结果。仓库里保留失败和部分达到的记录，它们同样有用。

## 证据与出处

包内容、文件清单和 SHA 在 [catalog.json](../../workflows/catalog.json) 和 [bundle-status.json](../../workflows/bundle-status.json) 里，生成与校验流程见 [workflows/README.md](../../workflows/README.md)。

## 怎么确认这一步成功了

1. 工作流能打开，节点没有报红，`LoadImage` 指向的文件确实存在。
2. 提交后能拿到输出图，而不是只有一条成功的 API 记录。
3. 你对照了功能报告里这一项的判定，知道自己拿到的是「通过」「部分达到」还是「未达到」。
4. 如果你改过提示词或图片，你重新跑过一遍，没有拿旧图当新结果。

## 卡住了看哪里

- 工作流打开就报缺节点：缺的是自定义节点，回 [02 章](./02-windows-setup.md) 第 4 步或 [03 章](./03-ubuntu-rocm.md) 的依赖那节。
- 图片找不到：`LoadImage` 里用的是 `ModelLibrary` 开头的文件名，确认文件已经复制进 `input`。
- 分阶段工作流出不来图：先确认编码那一步真的完成了，再确认服务是用指定配置重启的。
- 复现结果和报告对不上：先看 [排障](./07-troubleshooting.md)，再看 [AMD 卡适配矩阵](./08-amd-matrix.md) 确认你的卡在不在已验证那一档。
