# BFS 头部替换工作流与权重核查

核验日期：2026-10-19。本文只核对公开的 BFS 上游模型卡、ComfyUI 工作流和本机已有 Kroma API；不是公众号原文，也不证明刘悦视频使用了这些 LoRA。相关普通双图参考路径可以独立尝试，本文只说明怎样复现 BFS 明确公开的专用方案。未下载权重、安装节点或运行 GPU。

## 可选 LoRA 与精确文件

| 目标基础模型 | BFS LoRA | 文件字节数 | SHA-256 | 说明 |
|---|---|---:|---|---|
| Qwen Image 2.1 | [`bfs_head_v1.1_qwen_2.1.safetensors`](https://huggingface.co/Alissonerdx/BFS-Best-Face-Swap/resolve/main/bfs_head_v1.1_qwen_2.1.safetensors) | 260,096,144 | `d1d748d5601077f3b6d05766f6823510e901970d916afa404a97e85dc92fa88e` | 作者文档推荐；更重视头部角度保真。 |
| Qwen Image 2.1 | [`bfs_head_v1.1_alternative_qwen_2.1.safetensors`](https://huggingface.co/Alissonerdx/BFS-Best-Face-Swap/resolve/main/bfs_head_v1.1_alternative_qwen_2.1.safetensors) | 318,821,008 | `c5332bbc2f826856e7a09bce9740e97d39514b849368212e1f2c3c2c2d81c217` | 作者称其表情跟随更强，平均头部姿态误差略高。 |
| Krea 2 | [`bfs_head_swap_v1.1_krea2.safetensors`](https://huggingface.co/Alissonerdx/BFS-Best-Face-Swap/resolve/main/bfs_head_swap_v1.1_krea2.safetensors) | 914,159,816 | `abc6c468c578b36e6bd960106ad5886afd3f5321e4fe2de26c05bb5c6585b836` | Krea 2 专用 V1.1 头部替换 LoRA。 |

字节数和 SHA-256 来自 Hugging Face 原始 LFS 指针（Qwen 推荐版、Qwen alternative、Krea 2）。下载页面上显示的 MB 是四舍五入值。三份文件放入 `ComfyUI/models/loras/`。BFS Qwen 指南明确要求 **Qwen Image 2.1 base**，并注明它与 Qwen Image Edit 2509/2511 权重分开；文档没有声明 Turbo 或任意 GGUF 量化权重兼容。

## Qwen Image 2.1 BFS 接法

官方 [Qwen 2.1 BFS 指南](https://huggingface.co/Alissonerdx/BFS-Best-Face-Swap/blob/main/docs/qwen-image-2.1.md)及其[ComfyUI 工作流 JSON](https://huggingface.co/Alissonerdx/BFS-Best-Face-Swap/resolve/main/workflows/Head%20Swap%20V1%20Qwen%202.1%20Workflow.json)指定了基础模型、文本编码器、VAE 和两张图的顺序。工作流中主干为：

```text
UNETLoader (Qwen Image 2.1) -> LoraLoaderModelOnly (BFS, strength 1.0) -> KSampler.model
CLIPLoader (Qwen3-VL 8B, type=qwen_image) -> TextEncodeQwenImage21.clip
VAELoader (Qwen Image 2.1 VAE) -> TextEncodeQwenImage21.vae / VAEDecode.vae
目标图 -> TextEncodeQwenImage21.images.image_1
参考头部图 -> TextEncodeQwenImage21.images.image_2
TextEncodeQwenImage21 positive/negative -> KSampler -> VAEDecode
```

该工作流列出的参考模型文件名是 `qwen_image_2.1_int8_convrot.safetensors`、`qwen3vl_8b_int8_convrot.safetensors`（CLIP 类型 `qwen_image`）和 `qwen_image_2.1_vae_bf16.safetensors`。工作流本身还放有一个独立的 Pruna 8-step 加速 LoRA；BFS 文档说它不是 BFS 的组成部分，可禁用，不要把它和上述头部替换 LoRA 混为一项。

完整工作流 JSON 还含 KJNodes 的 `ImageResizeKJv2` 与 rgthree 的图片比较节点；若直接导入原图，需要相应自定义节点包。它们是工作流辅助节点，不是头部替换 LoRA 或主模型。

输入顺序固定：**image_1 是要保留身体、姿势、构图、光照和环境的目标底图；image_2 是提供身份、发型等特征的参考头部**。交换两张图会交换目标角色。BFS 起始指令以 `head_swap:` 开头，要求替换 image_1 的头部、保留 image_2 的身份特征，并沿用 image_1 的视线方向、头部旋转和微表情；精确原始模板见上面的工作流与指南。建议先用 LoRA 强度 1.0。

这是一套专用 BFS 配方。它不意味着所有普通双图参考换头都必须装 BFS；普通图像编辑工作流可以另行试跑。反过来，不能因为现有 Qwen Q4 GGUF 能加载双图，就宣称已复现 BFS 配方：BFS 发布工作流明确列出的是上述 safetensors 主模型/编码器/VAE，未明确认证本机 Turbo 或其他 GGUF 变体。

## Krea 2 BFS 接法

官方 [Krea 2 BFS 指南](https://huggingface.co/Alissonerdx/BFS-Best-Face-Swap/blob/main/docs/krea-2.md)和[配套工作流 JSON](https://huggingface.co/Alissonerdx/BFS-Best-Face-Swap/resolve/main/workflows/Head%20Swap%20Krea%202%20-%20V1%20Simple%20Workflow.json)指定 `bfs_head_swap_v1.1_krea2.safetensors`。工作流说明列出的基础资产为 `krea2_turbo_fp8_scaled.safetensors`（或 Krea 2 Raw BF16）、`qwen3vl_4b_fp8_scaled.safetensors`（CLIP 类型 `krea2`）和 `qwen_image_vae.safetensors`。

关键节点路径为：

```text
UNETLoader (Krea 2) -> LoraLoaderModelOnly (BFS Krea 2, strength 1.0)
  -> Krea2EditModelPatch -> KSampler.model
目标底图 -> VAEEncode / Krea2EditModelPatch.source_latent
        └-> Krea2EditGroundedEncode.image
参考头部 -> Krea2EditModelPatch.source_latent_b
        └-> Krea2EditGroundedEncode.image_b
CLIPLoader (Qwen3-VL 4B, type=krea2) -> Krea2EditGroundedEncode.clip
Krea2EditGroundedEncode -> KSampler conditioning -> VAE decode
```

提示词为 `head_swap: replace the head with the reference head.` 目标图放主输入 `image` / `source_latent`，参考头部放第二输入 `image_b` / `source_latent_b`；遵循“底图在前、参考头部在后”。随附 JSON 的第二图组标注为可选并默认关闭，需要两图时要启用它。JSON 中 `Krea2EditGroundedEncode` 和 `Krea2EditModelPatch` 标记为 `comfyui-krea2edit` v1.2.2；完整原图还含 KJNodes 的 `ImageResizeKJv2` 工具节点。照搬 workflow JSON 时要准备这些自定义节点。节点包维护者的[上游仓库](https://github.com/lbouaraba/comfyui-krea2edit)说明这两个 Krea 专用节点承担图像语义 grounding 与模型 patch，普通 `CLIPTextEncode` 不能替代它们。

有一处值得加载前核对：Krea JSON 的模型下载元数据指向 `krea2_turbo_fp8_scaled.safetensors`，但 `UNETLoader` 内嵌的默认 widget 文本写作 `Downloads/krea2_turbo_int8_convrot.safetensors`。报告保留这两个可见值，不替作者猜测哪个是当前推荐默认。该 JSON 的采样节点显示 8 步；其旁注给出 Turbo 8/10/12 步的调节说明，做复现时应以实际选用的 base/LoRA 及自己的试验为准。

## Kroma V0.3.1 Turbo OPD Q2_K

截至核验日，在 [BFS 仓库文件树](https://huggingface.co/Alissonerdx/BFS-Best-Face-Swap/tree/main)和 Krea 2 指南中没有找到 Kroma 专用头部 LoRA、Kroma 工作流或明确兼容说明。BFS 公开的 Krea 2 头部方案针对 Krea 2，不等于 Kroma 兼容。

本机旧试验的 [`kroma-api.json`](../../../trials/2026-10-18/kroma-api.json)实际载入 `kroma-v0.3.1-turbo-opd-Q2_K.gguf`，配 `qwen3vl_4b_fp8_scaled.safetensors`（CLIP 类型 `krea2`）和 `qwen_image_vae.safetensors`。CLIP 类型相同只是编码器配置相同，不能由此推导 LoRA 与 OPD Q2_K 扩散权重兼容。当前可把 Krea 2 BFS 文件视作**未验证的实验候选**，不能写成官方支持；也可先试普通双图编辑路径，但需要独立记为非 BFS 验证。

## 来源

- BFS Qwen Image 2.1 [指南](https://huggingface.co/Alissonerdx/BFS-Best-Face-Swap/blob/main/docs/qwen-image-2.1.md)；[Qwen 工作流](https://huggingface.co/Alissonerdx/BFS-Best-Face-Swap/blob/main/workflows/Head%20Swap%20V1%20Qwen%202.1%20Workflow.json)；[推荐版 LFS 指针](https://huggingface.co/Alissonerdx/BFS-Best-Face-Swap/raw/main/bfs_head_v1.1_qwen_2.1.safetensors)；[alternative LFS 指针](https://huggingface.co/Alissonerdx/BFS-Best-Face-Swap/raw/main/bfs_head_v1.1_alternative_qwen_2.1.safetensors)。
- BFS Krea 2 [指南](https://huggingface.co/Alissonerdx/BFS-Best-Face-Swap/blob/main/docs/krea-2.md)；[Krea 工作流](https://huggingface.co/Alissonerdx/BFS-Best-Face-Swap/blob/main/workflows/Head%20Swap%20Krea%202%20-%20V1%20Simple%20Workflow.json)；[Krea LoRA LFS 指针](https://huggingface.co/Alissonerdx/BFS-Best-Face-Swap/raw/main/bfs_head_swap_v1.1_krea2.safetensors)；[Krea 节点仓库](https://github.com/lbouaraba/comfyui-krea2edit)。
