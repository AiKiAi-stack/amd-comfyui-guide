# Flux.3-5.6B-UN：ModelScope 仓库选择核验

核验日期：2026-10-20。只读查找公开 ModelScope 页面/API 和本机已有文件；没有下载大权重、运行 GPU 或修改环境。结论针对 ModelScope 候选，不替代作者 Compshare/Quark 整合包检查。

## 结论

截至本轮检索，没有找到可确认属于作者 `Flux.3-5.6B-UN`、Sakura/uncensored FLUX3 encoder，或可证实为该作者 4 步方案的 LoRA/checkpoint。ModelScope 找到的 `junwenlu/flux-3-image-klein-ComfyUI` 明确是标准 BFL FLUX3 Klein 蒸馏 INT8 包：README 写的是 15 步 T2I，含 T2I 与图像编辑工作流；没有 4 步 LoRA 文件或 UN 标识。它可以作为**标准 FLUX3 Klein 的加载、基础生成/编辑对照**，不能作为作者 UN 的身份、4 步设置或特色功能验证。页面称其作者实测 RTX 5060 Ti 16GB；不能据此确认 RX 6650 XT 8GB/16GB RAM 可运行。

对这个标准包，ModelScope 文件 API 在固定仓库快照 `89a908e886b5c8b08001488bb65691703375968e` 返回了三个 LFS 权重和两个小型工作流文件的字节数与 SHA-256。文件各自的上传 revision 不同，均已列在 `trials/2026-10-20-flux3/selection.json`。API SHA 是远端元数据，本轮没有下载权重来做本地哈希复核。

## 精确目标搜索

以 `Flux.3-5.6B-UN`、`Flux.3-Image-5.6B-UN`、`Flux3 Klein 4-step LoRA`、`Flux3 Sakura/uncensored` 等词检索 ModelScope 的公开索引，没有出现匹配该目标的结果。ModelScope 有一个名字含 `Uncensored` 的 [`FluxLora/enhanceaiteam-Flux-Uncensored-V2`](https://modelscope.cn/models/FluxLora/enhanceaiteam-Flux-Uncensored-V2)，其卡片明确限定基础模型为 `black-forest-labs/FLUX.1-dev`，不是 FLUX3/Klein，因此不是兼容候选。检索未命中不能证明 ModelScope 上绝对没有未索引或私有文件；本报告只说“目前未找到可证实匹配项”。

ModelScope 的 [BFL 官方 FLUX 3 Image Klein ComfyUI 仓库](https://www.modelscope.cn/models/black-forest-labs/flux-3-image-klein-comfy)列出官方标准 Klein base/distilled 权重，并非作者 UN。第三方 `junwenlu` 仓库的模型卡也明确将源仓库归为这个 BFL 官方 ComfyUI 发布。

## 可复核的标准基线仓库

候选：[`junwenlu/flux-3-image-klein-ComfyUI`](https://www.modelscope.cn/models/junwenlu/flux-3-image-klein-ComfyUI)。页面卡片称它由蒸馏主干、Qwen3-VL-4B 编码器、VAE 与两个 ComfyUI 工作流组成，并称在 RTX 5060 Ti 16GB 上验证；名称、README 和 source acknowledgement 均指向 BFL 标准 FLUX3 Klein。

固定快照：`89a908e886b5c8b08001488bb65691703375968e`（ModelScope API 的 master HEAD，2026-10-16 12:36:42 UTC 的 README 更新）。API 查询：[固定快照文件清单](https://www.modelscope.cn/api/v1/models/junwenlu/flux-3-image-klein-ComfyUI/repo/files?Revision=89a908e886b5c8b08001488bb65691703375968e%26Recursive=True)。权重文件与仓库卡片的标称大小不同于精确 byte 数，是 GB/GiB 显示口径差别；以 API `Size` 和 SHA 为下载校验值：

| 用途 | 仓库相对路径 | API 字节数 | SHA-256 | 文件 revision |
|---|---|---:|---|---|
| 标准 Klein 蒸馏 INT8 主干 | `diffusion_models/flux3_image_klein_sd_int8_convrot.safetensors` | 5,827,874,779 | `847d8933548afd93df4af2cac2498e70891bf28d9dae06d695f536992e168fe2` | `1c4e5e30ae24c6faced41c3ba213bd500e1a753b` |
| 标准 Qwen3-VL-4B INT8 encoder | `text_encoders/qwen3vl_4b_int8_convrot.safetensors` | 4,858,559,240 | `32de113cbf8282b02cbff0794b637b9d6676da09314a1db5a30bcea9bf4ee01c` | `7a9e9eb4884c49d7415cb12274362b69b3d90d64` |
| 标准 Flux2 VAE | `vae/flux2-vae.safetensors` | 336,211,292 | `868fe7b343cc8f3a19dbcfcafbc3d5f888802be3f89bd81b65b3621a066ce8f3` | `99351fbbd34547927fad5e0da71cfaa40687e312` |
| T2I 工作流 | `workflows/Image_T2I_Flux3-Klein.json` | 7,113 | `4c3f9bc20fe2b4cbe6a4561737f9c7bd9b6ceaa5047c99d283be1a18f14aedc8` | `20e7c40ebfc764e7c84301b563e09012a0865d04` |
| 编辑工作流 | `workflows/Image_EDIT_Flux3-Klein.json` | 10,255 | `c5772d9c8de52b29b7fc92f68e26a9aed598f1a1f3e853fcec3af70d3297754c` | `82e0ad5e23839ce4379315a0e8b2e673f103aad1` |

从该固定快照只筛选三个权重时，约 11.02 GB 十进制（10.26 GiB）；如果也要保留可复核节点配方，可额外取两个小 JSON。仓库没有独立 prompt-upscaler 权重，不能用这个包验证作者页面声称的“自动提示词”。

### 工作流参数核对

本轮通过 ModelScope 小文件 API 读取了两份 JSON，没有读取/下载模型权重：

- T2I 工作流节点是原生 `UNETLoader`、`CLIPLoader(type=flux3)`、`VAELoader` 等；KSampler 为 **15 步、CFG 1、`er_sde` / `simple`**。
- 图像编辑工作流使用 `VAEEncode`、`ReferenceLatent` 等节点；KSampler 为 **16 步、CFG 1、`euler` / `simple`**。
- 两份 JSON 均没有 LoRA 节点。README 的 15 步建议与 T2I workflow 一致；编辑工作流不是同一采样设置。故不能将“15 步标准 Klein 蒸馏包”描述为作者 4 步包。

该仓库 README 声称 1024×1024 T2I 约 12GB、编辑约 13GB 峰值，并称 8–12GB 显存可借助卸载运行但变慢；其实际验证卡为 RTX 5060 Ti 16GB。对 RX 6650 XT 8GB 的峰值、ROCm 内核、速度和 16GB 系统内存压力均无实测证据。若父代理要用它做标准版加载对照，应该在结果中单独标作 `standard-flux3-klein-baseline`，不要标成 `Flux.3-5.6B-UN`。

## 本机 encoder / VAE 哈希对照

以下本机 SHA 是本轮 `Get-FileHash` 对现有文件重新计算的结果，并与历史下载清单一致：

| 本机现有文件 | 本机 bytes / SHA-256 | ModelScope 候选对应件 | 完全匹配？ |
|---|---|---|---|
| `ComfyUI/models/text_encoders/qwen3vl_4b_fp8_scaled.safetensors`（Comfy-Org/Krea-2） | 5,242,467,968 / `54bd5144df0bbc25dd6ccadfcb826b521445a1b06ae5a42570bdd2974ca87094` | ModelScope `qwen3vl_4b_int8_convrot.safetensors`, 4,858,559,240 / `32de113c…` | 否：本机 FP8 scaled 与候选 INT8 ConvRot 不同文件。两者都属 Qwen3-VL-4B 家族；本机 ComfyUI 原生 `flux3` encoder 分支接受 Qwen3-VL-4B 是复用尝试的依据，但具体权重兼容和输出未测。 |
| `ComfyUI/models/vae/flux2-vae_small.safetensors`（Comfy-Org/MOSS-Image） | 249,521,340 / `d8d52ba036475f5fb07c8b435e176d3d97ebfa82f0d1a1c317f9cc1e25bd013b` | ModelScope `flux2-vae.safetensors`, 336,211,292 / `868fe7b…` | 否：文件名变体、体积、SHA 都不同；Flux2 家族相同只支持列为未验证候选，不能替换后称已复现该工作流。 |

两个本机文件的来源和历史校验记录分别见 [Kroma 下载清单](../trials/2026-10-18/kroma-download.json) 与 [MOSS 下载清单](../trials/2026-10-18/moss-download.json)。没有发现本地已有候选与 ModelScope 标准包 encoder/VAE 文件 SHA 完全一致。

## 给父代理的选择建议

若目标是先验证本机的**标准 FLUX3 原生加载与基本出图路径**，上述 ModelScope 蒸馏主干是当前能给出固定 revision、具体文件和 SHA-256 的可复核候选；它确有 T2I 和单图编辑工作流。最好把它作为独立标准基线记录，和作者整合包目标分开，且测试输出不能算作 `UN` 成功。若目标必须是用户所说的作者 `Flux.3-5.6B-UN` 与 4 步实现，当前 ModelScope 证据不足以选这个仓库冒充目标；需要作者镜像/归档内部权重或作者明确权重映射、4 步配置后再确认。

本文件与 [selection.json](../trials/2026-10-20-flux3/selection.json) 保存候选标识、远端元数据及本地 hash 对照，供实际下载前复核。
