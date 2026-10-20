---
frameworks: PyTorch
license: other
license_name: flux-kommunity-license
language:
  - en
tasks:
  - image-to-image
base_model:
  - black-forest-labs/flux-3-image-klein-comfy
base_model_relation: quantized
---
# FLUX.3 Klein ComfyUI 版（int8_convrot 量化组合包）

FLUX.3 Klein 的 ComfyUI 本地部署组合包：蒸馏版扩散模型（int8_convrot 量化）+ Qwen3-VL-4B 文本编码器（int8 量化）+ VAE + 开箱即用的文生图/图像编辑工作流。已在 RTX 5060 Ti (16GB) 实测通过。

## 模型介绍

- 原始模型：[black-forest-labs/flux-3-image-klein-comfy](https://www.modelscope.cn/models/black-forest-labs/flux-3-image-klein-comfy)（Black Forest Labs 官方 ComfyUI 发行版）
- 本仓库挑选其中一套经过实测验证的最小组合（int8_convrot 量化路线，蒸馏版 15 步快速出图），并附调好的工作流
- 量化格式：int8_convrot（8-bit + 旋转换位），与 Qwen Image 2.1 官方量化同族，ComfyUI 原生支持，稳定且画质损失极小
- 文本编码器为 Qwen3-VL-4B（多模态），**ComfyUI 的 CLIPLoader 类型必须选 `flux3`**（选 `flux2` 会报维度错误）

## 文件清单

| 文件 | 大小 | 作用 |
|---|---|---|
| `diffusion_models/flux3_image_klein_sd_int8_convrot.safetensors` | 5.43 GB | 扩散模型（蒸馏版，sd = step-distilled） |
| `text_encoders/qwen3vl_4b_int8_convrot.safetensors` | 4.52 GB | 文本编码器（Qwen3-VL-4B，type=flux3） |
| `vae/flux2-vae.safetensors` | 0.31 GB | VAE（与 FLUX.2 共用） |
| `workflows/Image_T2I_Flux3-Klein.json` | 8 KB | 文生图工作流（中文标注） |
| `workflows/Image_EDIT_Flux3-Klein.json` | 9 KB | 图像编辑工作流（ReferenceLatent 方案） |

## 快速开始

### 1. 目录结构

按裸文件名放入 ComfyUI 对应目录（**不要改名、不要挪进子文件夹**，工作流按文件名引用）：

```
ComfyUI/
└── models/
    ├── diffusion_models/flux3_image_klein_sd_int8_convrot.safetensors
    ├── text_encoders/qwen3vl_4b_int8_convrot.safetensors
    └── vae/flux2-vae.safetensors
```

工作流 JSON 放到 `ComfyUI/user/default/workflows/` 或直接在 ComfyUI 界面导入。

### 2. 依赖

- ComfyUI ≥ v0.41.0（FLUX.3 支持已合入主线）
- 文本编码节点：CLIPLoader，**类型选 `flux3`**
- 推荐安装 `sageattention`（注意力加速，实测 3 倍提速）与匹配的 torch 版本

### 3. 出图步骤

1. 下载上述 3 个模型文件放入对应目录
2. 在 ComfyUI 中加载 `workflows/Image_T2I_Flux3-Klein.json`
3. 确认三个加载节点已选中对应文件，直接 Queue

## 硬件需求

| 工作流 | 显存峰值 | 实测 |
|---|---|---|
| 文生图 1024×1024 | ~12 GB | RTX 5060 Ti 16GB：15 步约 6 秒/张（sageattention 加速后） |
| 图像编辑 1024×1024 | ~13 GB | 同上，编辑指令式修改，非编辑区域保持不变 |

8-12 GB 显存可正常跑（ComfyUI 自动分层卸载），速度相应变慢。

## 规格与限制

- 蒸馏版推荐采样：`er_sde` / 15 步 / **cfg = 1**（不使用负向提示，负向条件用 ConditioningZeroOut 或留空）
- 分辨率：1024×1024 为基准，支持多种宽高比
- 图像编辑：把原图 VAE 编码后通过 ReferenceLatent 挂到正向条件，配编辑指令即可；支持多轮迭代编辑
- 已知坑：CLIPLoader 类型选 `flux2` 会报 `shapes cannot be multiplied (512x7680, 3072x20480)`，选 `flux3` 即可

## 致谢 / 来源

- 模型与权重：[black-forest-labs/flux-3-image-klein-comfy](https://www.modelscope.cn/models/black-forest-labs/flux-3-image-klein-comfy)
- 工作流基于官方发行版整理，替换为实测稳定的量化组合并做中文标注

