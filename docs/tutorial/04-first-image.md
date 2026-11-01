# 04 · 出第一张图，再单独重跑一项

这一章让服务出一张图，然后重跑一条真正的编辑案例。做完你手上有一份能对照的记录：API 状态、history、输出 SHA 和一张自己看过的图。

顺序别跳：先确认 GPU 是通的，再只下一个模型，跑通一张，最后才换第二个模型。

## 第 1 步：先验证 GPU

还没跑过 GPU 检查，就先跑一次。Windows 用 `.venv\Scripts\python.exe scripts/check_gpu.py`，Linux 用 `runtime/ubuntu/.venv/bin/python scripts/check_gpu.py`，判据在 [02](./02-windows-setup.md) 第 3 步和 [03](./03-ubuntu-rocm.md) 第 3 步。

这一步不通过，下面的下载和启动都是白跑。

## 第 2 步：只下一个模型

第一次别把整套模型都拖下来，选一个。下载清单记了来源仓库、固定 revision、文件名、字节数和 SHA-256，公开快照里留了一份格式样例：`evidence/2026-10-20-zimage/download-manifest.json`。文件要放到 `runtime/ComfyUI/models/` 下对应的 `diffusion_models`、`text_encoders`、`vae`、`loras` 或 `checkpoints` 里。

历史清单里的 `target` 是换过路径的实验目录示例，别原样当成自己机器上的路径。用仓库的下载工具，它只按你选的清单下，并重新映射到 runtime：

```powershell
.venv\Scripts\python.exe scripts/download_models.py 你的下载清单.json --comfy runtime/ComfyUI
```

Kroma 这组用的清单在原始实验记录里，没有进公开快照；换成你手上任何一份清单路径都能跑，格式参考上面那份 `download-manifest.json`。

Kroma 清单大约 11.46 GB，这个数字是磁盘占用，不是运行时的显存占用。所有模型都要遵守各自的上游许可，仓库不分发权重。

这个下载工具没有断点续传：失败会留下 `.part` 文件，重试从头开始，校验通过才改名成最终文件。

## 第 3 步：启动服务

从 Kroma Q2 的低分辨率文生图起步。新开一个终端，用 AMD 环境：

```powershell
.venv\Scripts\python.exe -u runtime/ComfyUI/main.py --listen 127.0.0.1 --port 8188 --cpu-vae --disable-async-offload --fast-disk
```

等 `http://127.0.0.1:8188` 能打开。首次导入和冷加载可能要几分钟，别拿采样那 17.8 秒去推算从启动到出图的时间。

## 第 4 步：提交一条实际测过的 API 图

```powershell
.venv\Scripts\python.exe scripts/replay_workflow.py evidence/2026-10-18/kroma-api.json --out runs/kroma-first
```

脚本先检查图里的节点在不在，再提交到本地 ComfyUI，然后把这次提交、history、输出副本和 SHA-256 都存下来，不会覆盖仓库里的历史证据。

跑完 `runs/kroma-first` 里应该有输出图，同时留下了这次提交的 history。只看到一张图、没有 history，说明记录没存全。

API 图和带坐标的 UI workflow 是两回事。把 `api.json` 拖进界面，不保证节点布局能还原。

这条 API 图的记录结果是 512×512、4 步、CFG 1、Euler/simple，算上冷加载大约 285 秒。它只验证这套 Q2 配方，不是原作者所有功能的完整复现。

## 第 5 步：重跑一个编辑案例

先把公开的输入素材放进运行环境，再挑报告卡片里那条 `api.json`：

```powershell
Copy-Item workflows/input/* runtime/ComfyUI/input -Recurse -Force
.venv\Scripts\python.exe scripts/replay_workflow.py evidence/2026-10-19-features/cases/moss-text/api.json --out runs/moss-text-new
```

切到 MOSS 之前先退出原来的服务，在新终端里设 `$env:COMFY_GFX1032_INT8_FALLBACK='1'` 再启动，并把配套权重下好。Turbo-UN 的实测配置还要加 `--disable-dynamic-vram --lowvram`，同时把工作流里的 Qwen prefix cache 关掉。不同模型的配置见报告，只改文件名然后照搬全部设置是不行的。

有些 case 的 `api.json` 是实际提交的整批图，会跑好几个保存节点；`single-api.json` 才是拆出来的独立图。提交前先看一眼节点和模型文件名，免得意外跑一整批。

`evidence/` 里那些原始脚本是历史代码来源，保留了旧目录和当时的进程管理假设。现在通用的入口是 `scripts/`。历史绝对路径不要当安装命令直接用。

## 证据与出处

模型来源、固定 revision、字节数和 SHA-256 记在下载清单里，公开的格式样例是 `evidence/2026-10-20-zimage/download-manifest.json`；逐项结果和目视判定在 [功能报告](../../report/feature-report.md)。

## 和你看到的不一样时

- 页面打不开：回 [Ubuntu + ROCm](./03-ubuntu-rocm.md) 的启动那节，确认端口和服务状态。
- 报节点不存在：API 图里的自定义节点没装，回 [02](./02-windows-setup.md) 第 4 步。
- 出图是黑的或全是噪声：先去 [排障](./07-troubleshooting.md) 对着症状找，别急着重跑。
- 想换模型：先读 [模型选择](./05-models.md)，再看 [工作流库](./06-workflows.md)。

## 过关条件

1. 服务页面打得开，`runs/kroma-first` 目录里出现了输出图。
2. 这批记录里的 API 状态是成功，history 也存下来了，不是只留一张图。
3. 你能说清这张图是 512×512、4 步、CFG 1、Euler/simple，冷加载大约 285 秒。
4. 你打开图看了一眼：没黑、没满屏噪声、主体对、文字拼对了（如果图里有字）。

API 返回 success 只说明请求跑完了。图是不是对的，要自己看。
