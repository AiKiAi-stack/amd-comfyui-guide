# 模型功能工作流库

本库覆盖7个模型系列、40项功能，提供268份WebUI工作流及对应API文件。本机已将184份推荐工作流安装到WebUI左侧的“模型功能库”。工作流能打开与模型效果通过分别记录，具体结果见[功能汇报](../report/index.html)。

## 在本机使用

打开ComfyUI左侧“工作流 → 模型功能库”，按模型和功能选择文件。也可以下载单份UI JSON，通过“打开工作流”载入。

需要分步运行的方案，先按该项说明完成编码，再按指定配置重启服务并运行出图工作流。本机保留了原测试的编码结果，输入不变时可直接运行出图步骤；修改提示词、图片或参考顺序后，必须重新编码，并更新出图节点中的文件路径和SHA256。

Windows工作流保留当时的权重、提示词和参数。它们在当前前端通过了导入检查，Linux实际结果请看各功能自己的记录。

## 在其他机器使用

[完整包](https://github.com/AiKiAi-stack/amd-comfyui-guide/releases/download/model-feature-workflows-2026-10-26/model-feature-workflows.zip)包含UI、API、输入图片及经过SHA256校验的编码/描述文件，不含模型权重。[轻量包](https://github.com/AiKiAi-stack/amd-comfyui-guide/releases/download/model-feature-workflows-2026-10-26/model-feature-workflows-light.zip)不含这些编码文件，需要先运行编码步骤。

解压后，将包内input的内容复制到目标ComfyUI/input，再打开ui目录中的工作流。模型文件和启动配置列在各项使用步骤中。输入文件采用ModelLibrary开头的统一名称；原路径映射、文件SHA和完整参数见[catalog.json](catalog.json)。

## 维护者：重建工作流库

依次运行：

```bash
python scripts/build_workflow_library.py
node scripts/convert_workflow_library.cjs
python scripts/install_workflow_library.py
python scripts/build_platform_report.py
```

转换脚本通过实际ComfyUI前端导出、重新载入并核对参数，不执行模型推理。安装器遇到用户自行修改的同名工作流会停止，保留修改。完整下载包中的safetensors是编码结果，不是模型权重。
