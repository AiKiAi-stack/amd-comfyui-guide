# RX 6650 XT 试机步骤

这是 2026-10-19 本机验证后的操作入口，所有路径位于 D:。来源和每次成败证据见同目录 `README.md`。此处的 Python 脚本通过本机 ComfyUI API 提交任务；`*-api.json` 是 API 图，不是带节点位置的可视化工作流。

权重已经按类型放入 `D:/AI/barely-comfy\ComfyUI\models\diffusion_models`、`text_encoders`、`vae`、`loras`。本轮下载的 10 个文件均有大小及 SHA-256 校验凭据（同目录 `*.verified.json`）；固定 revision 的完整清单是 `qwen-turbo-download.json`、`qwen-turbo-uncensored-download.json`、`kroma-download.json`、`moss-download.json` 和 `moss-dmd-download.json`。无需再安装 CUDA 版 PyTorch或重复下载。

## 1. 启动已有 AMD 环境

如果 `http://127.0.0.1:8188` 已能打开，直接到下一步。否则在 PowerShell 执行：

```powershell
Set-Location D:/AI/barely-comfy
.\.venv\Scripts\python.exe -u .\ComfyUI\main.py --listen 127.0.0.1 --port 8188 --fast-disk --cpu-vae --disable-async-offload
```

首次导入可能需要数分钟；等日志出现 `To see the GUI go to: http://127.0.0.1:8188`。这套命令已完成下列两个 Qwen 试验。原始配置在 768 像素参考图编辑时出现过原生崩溃，所以当前从 512 像素开始。

## 2. 跑已验证的普通 Qwen Turbo

另开一个 PowerShell：

```powershell
Set-Location D:/AI/barely-comfy
.\.venv\Scripts\python.exe -u .\trials\2026-10-18\run_qwen_turbo.py
```

脚本使用 512×512、8 步、CFG 1、Euler 和官方 Turbo sigma 列表。它输出任务 ID，等待完成后写 `qwen-turbo-history.json`。本机首次冷运行约 10 分 53 秒，不能据此预估其他分辨率或模型的速度。

结果图片：`D:/AI/barely-comfy\ComfyUI\output\Liuyue_Qwen21_Turbo_RX6650XT_00001_.png`。

## 3. 跑已验证的 Qwen 基础版参考图编辑

```powershell
Set-Location D:/AI/barely-comfy
.\.venv\Scripts\python.exe -u .\trials\2026-10-18\run_qwen_edit.py 512
```

脚本将已有的橘猫图复制到 `ComfyUI\input\liuyue-qwen-base-source.png`，要求把猫改成白猫，保持街景与构图。使用 512×512、15 步、CFG 1。此任务约 7 分 3 秒完成，当时部分组件已缓存。该试验是单张参考图编辑，尚未验证多图参考、人物身份替换或带遮罩的局部重绘。

结果图片：`D:/AI/barely-comfy\ComfyUI\output\Liuyue_Qwen21_Base_Edit_RX6650XT_00001_.png`。

## 4. 其他组的入口和限制

- Kroma：`run_image_model.py kroma`，Q2 GGUF、512×512、4 步；已在本机成功生成狐狸图，总用时约 4 分 45 秒（含加载），采样约 17.8 秒。输出 `ComfyUI/output/Liuyue_Kroma031_Q2_4step_RX6650XT_00001_.png`。建议在新启动的 ComfyUI 服务中单独运行。
- MOSS：启用下方兼容开关后，`run_image_model.py moss` 的 SFT INT8、512×512、50 步基础测试已成功（缓存后约 3 分 18 秒）；`run_image_model.py moss8` 的 LoRA 强度 1、8 步、CFG 1 候选也成功（含 LoRA 初始化约 3 分 8 秒）。当前作者未明示完整 sampler/scheduler/shift 配方；本轮用 Euler/sgm_uniform、AuraFlow shift 5，核心内置 MOSS 的 timestep multiplier 必须保持为 1。正确基础图为 `Liuyue_MOSS_SFT_INT8_50step_RX6650XT_00002_.png`；`00001_` 是已作废的错误时间尺度噪声图。
- Turbo-Un：`run_qwen_turbo.py uncensored` 是实验组合，已经触发过 GGUF 编码器卸载的原生崩溃。普通 Turbo 成功不能算作这个组合成功。
- MiniMax H3：基础文件合计约 42.47 GB，本轮因本机内存约束没有下载运行。

MOSS 的原生 INT8 算子在这块 gfx1032 显卡上报过 `HIPBLAS_STATUS_INVALID_VALUE`。本地兼容开关位于 `ComfyUI/custom_nodes/gfx1032_quant_fallback/__init__.py`，默认不启用。需要 MOSS 回退配置时，在新 PowerShell 中先设置环境变量，再按第 1 步启动服务：

```powershell
$env:COMFY_GFX1032_INT8_FALLBACK = '1'
```

等启动日志出现 `gfx1032 trial: INT8 GEMM disabled`，然后运行 MOSS 脚本。此配置按层解量化后使用浮点计算，仍保留量化权重存储。它也会影响该服务内其他量化模型，建议单独运行 MOSS。未来要关闭时，退出该服务，执行 `Remove-Item Env:\COMFY_GFX1032_INT8_FALLBACK` 后重新启动即可。

## 5. 判断是否真正完成

脚本显示 `DONE` 且 `status_str` 为 `success` 后，再查看对应图片。只有 `SUBMITTED` 表示已提交；服务器退出、黑图、噪声图、未达到编辑要求均不能视为可用。每个输出文件含 PNG 元数据，可保留作复现证据。
