# 04 · 第一张图与单项重跑

## 获取模型

首次只选一个模型，不下载全套。`evidence/2026-10-18/*-download.json` 与后续模型目录的 `download-manifest.json` 保存来源仓库、固定 revision、文件名、字节数与 SHA-256。下载到 `runtime/ComfyUI/models/` 对应的 `diffusion_models`、`text_encoders`、`vae`、`loras` 或 `checkpoints`。

历史清单中的 `target` 是经过替换的实验目录示例，不能原样当成本机路径。可使用仓库的独立下载工具，它只按选择的清单下载，并重新映射到 runtime：

```powershell
.venv\Scripts\python.exe scripts/download_models.py evidence/2026-10-18/kroma-download.json --comfy runtime/ComfyUI
```

Kroma 清单约 11.46 GB，不等于运行时显存占用。所有模型仍需遵守各自上游许可；仓库不分发权重。第一次下载本工具不实现断点续传，失败 `.part` 会保留，重试重新开始，校验通过才改为最终文件。

## 启动服务

以 Kroma Q2 的低分辨率文生图为起点。新开终端，使用 AMD 环境：

```powershell
.venv\Scripts\python.exe -u runtime/ComfyUI/main.py --listen 127.0.0.1 --port 8188 --cpu-vae --disable-async-offload --fast-disk
```

等 <http://127.0.0.1:8188> 可访问。首次导入和冷加载可能数分钟，不能用采样 17.8 秒推算从启动到出图的时间。

## 使用实际测试过的 API 图

```powershell
.venv\Scripts\python.exe scripts/replay_workflow.py evidence/2026-10-18/kroma-api.json --out runs/kroma-first
```

脚本先检查图中的节点是否存在，再提交到本地 ComfyUI，保存本次提交、history、输出副本与 SHA-256；不会覆盖仓库里的历史证据。API 图与带坐标的 UI workflow 不同，不能假定将所有 `api.json` 拖进界面都能恢复节点布局。

本例历史结果是 512×512、4步、CFG 1、Euler/simple：冷加载在内约 285 秒。它只验证此 Q2 配方，不是作者所有功能的完整复现。

## 重跑编辑案例

先把公开输入素材放入运行环境，再选择报告卡片的 `api.json`：

```powershell
Copy-Item ComfyUI/input/* runtime/ComfyUI/input -Recurse -Force
.venv\Scripts\python.exe scripts/replay_workflow.py evidence/2026-10-19-features/cases/moss-text/api.json --out runs/moss-text-new
```

切换到 MOSS 前先退出原服务，在新终端设置 `$env:COMFY_GFX1032_INT8_FALLBACK='1'` 再启动；下载其配套权重。Turbo-UN 的实测配置还需 `--disable-dynamic-vram --lowvram` 和工作流中的 Qwen prefix cache 关闭。不同模型配置见报告，不能只改文件名复用所有设置。

部分 case 的 `api.json` 是实际提交的整批图，会运行多个保存节点；`single-api.json` 才是拆出的独立图。先查看节点与模型文件名，避免意外运行整批。原始 `evidence/` 脚本是历史代码来源，保留了旧目录和进程管理假设；新的通用入口是上面的 `scripts/`，不要把历史绝对路径直接当成安装命令。

## 验收

查看输出：是否黑图/噪声、主体是否正确、输入关系是否保留、文字是否拼对。将本次 API 状态、耗时范围、失败栈和目视结论分开记录；即便 API success，噪声图也保留为失败证据。不要覆盖旧图冒充原任务成功。
