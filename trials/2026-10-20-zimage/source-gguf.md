# Z-Image Turbo GGUF：离线文章与权重源审计（2026-10-20）

本页是**只读来源核对**；没有下载本页所列 GGUF、启动 ComfyUI 或验证 RX 6650 XT 出图。来源是用户提供的离线文章 《Z-Image很稳，低显存GGUF模型和工作流！》（私人离线快照未公开），其 `metadata.json` 记载公众号「托尼不是塔克」、发布时间 2025-12-01 23:58 +08:00。这里只读取了离线文件及公开的 Hugging Face 模型页/API，未请求微信原文。文章所说的网盘工作流 JSON **未包含在离线目录**；下述节点与参数是 `images/006.png`、`images/008.png` 截图可见内容，并非已校验的可直接导入 JSON。

## 可复现文件

Hugging Face API `?blobs=true` 返回以下当时的仓库 revision、文件字节数和 LFS SHA-256。`jayn7` 是原模型的**第三方量化发布者**；`unsloth` 是文本模型的第三方量化发布者；原始 Z-Image 模型另见 [Tongyi-MAI/Z-Image-Turbo](https://huggingface.co/Tongyi-MAI/Z-Image-Turbo)。下载必须固定 revision 并按 SHA 验证，不能只依赖文件名。

| 用途 | 仓库 / revision / 仓库内路径 | 字节 | SHA-256 |
|---|---|---:|---|
| 文章倾向的图像扩散模型 Q4_K_M | [`jayn7/Z-Image-Turbo-GGUF`](https://huggingface.co/jayn7/Z-Image-Turbo-GGUF/tree/6e2dff8e3abd78051c1211fb5833a03818a2f3cc) / `6e2dff8e3abd78051c1211fb5833a03818a2f3cc` / `z_image_turbo-Q4_K_M.gguf` | 4,981,532,736 | `745ec270db042409fde084d6b5cfccabf214a7fe5a494edf994a391125656afd` |
| 更小的对照 Q3_K_M | 同仓库 / 同 revision / `z_image_turbo-Q3_K_M.gguf` | 4,123,753,536 | `0d01263fcc74b9813d03e62d122461ad759f2837ffeecefc0ef00451244b89e6` |
| Qwen 编码器 Q4_K_M 候选 | [`unsloth/Qwen3-4B-GGUF`](https://huggingface.co/unsloth/Qwen3-4B-GGUF/tree/22c9fc8a8c7700b76a1789366280a6a5a1ad1120) / `22c9fc8a8c7700b76a1789366280a6a5a1ad1120` / `Qwen3-4B-Q4_K_M.gguf` | 2,497,281,312 | `f6f851777709861056efcdad3af01da38b31223a3ba26e61a4f8bf3a2195813a` |
| **文章截图实际显示**的编码器 Q4_K_S | 同仓库 / 同 revision / `Qwen3-4B-Q4_K_S.gguf` | 2,383,310,112 | `78cea0ccfd5fd7af5761f7dfdeebd2ec8f04328be0f1e6f70e2213a6f1309bc9` |
| 更小的编码器 Q3_K_M | 同仓库 / 同 revision / `Qwen3-4B-Q3_K_M.gguf` | 2,075,618,592 | `e78ff54a67f3b3f57e637fbf0770d5b73c1e215ea7c0153980f1e8140c2b2486` |
| VAE，已有本地 verified 文件 | [`Comfy-Org/z_image_turbo`](https://huggingface.co/Comfy-Org/z_image_turbo/tree/6fc90a3b1b653e935a0d175e260736de25b84df5/split_files/vae) / `6fc90a3b1b653e935a0d175e260736de25b84df5` / `split_files/vae/ae.safetensors` | 335,304,388 | `afc8e28272cd15db3919bacdb6918ce9c1ed22e96cb12c4d5ed0fba823529e38` |

文章的 Q4_K_M 图像模型加**截图中的 Q4_K_S 编码器**合计 7,364,842,848 B（约 6.86 GiB），再加 VAE 为 7,700,147,236 B；如果两者都选 Q4_K_M，则 GGUF 文件合计 7,478,814,048 B。这些是**磁盘文件大小，不等于运行时显存/内存需求**。文件清单来自 [jayn7 API](https://huggingface.co/api/models/jayn7/Z-Image-Turbo-GGUF?blobs=true)、[unsloth API](https://huggingface.co/api/models/unsloth/Qwen3-4B-GGUF?blobs=true) 和 [Comfy-Org API](https://huggingface.co/api/models/Comfy-Org/z_image_turbo?blobs=true)。本机 `D:/AI/barely-comfy\ComfyUI\models\vae\ae.safetensors` 当前正好 335,304,388 B，实算 SHA-256 与上表相符，可复用。GGUF 权重的下载和最终校验由另一个执行流程记录；本页静态来源审计不代表实时下载状态。

## 工作流与节点兼容性边界

文章 `images/006.png` 所示平铺图：`UnetLoaderGGUF` → `ModelSamplingAuraFlow(shift=3)`；`CLIPLoaderGGUF` 以 `lumina2` 类型加载 **`Qwen3-4B-Q4_K_S.gguf`**，两个 `CLIPTextEncode` 连接正/负提示词；`VAELoader(ae.safetensors)`；`EmptySD3LatentImage(1024×1024,batch=1)`；`KSampler(9 steps,cfg=1,euler,simple,denoise=1)` → `VAEDecode` → `SaveImage`。扩散模型选择框截断成 `z_image_turbo-Q4_K_...`，只能结合文章文字判断作者**偏好** Q4_K_M，不能从截图独立证实尾缀 M。Qwen 量化档位则在 `images/008.png` 清楚显示为 **Q4_K_S**，不是 Q4_K_M。

本机 `D:/AI/barely-comfy\ComfyUI\custom_nodes\ComfyUI-GGUF` 已安装，当前 Git HEAD `373048b8403a7820620065210a691263d4da0a61`。其 `nodes.py` 注册 `UnetLoaderGGUF` 与 `CLIPLoaderGGUF`，将模型目录分别映射到 `models/diffusion_models` / `models/text_encoders`；`loader.py` 含 `lumina2`，`dequant.py` 含 Q4_K 和 Q3_K 解量化。因此节点**静态上具备**该图所需入口，但尚未通过本机 Windows/ROCm 真正加载或生成，不能称为兼容性实测。GGUF 项目发布页也把 [ComfyUI-GGUF](https://github.com/city96/ComfyUI-GGUF) 列为用法。`jayn7` 仓库另有 [`example_workflow.json`](https://huggingface.co/jayn7/Z-Image-Turbo-GGUF/blob/6e2dff8e3abd78051c1211fb5833a03818a2f3cc/example_workflow.json)，是可追溯的公开示例，但默认 Q8 图像模型与 Q8 编码器，**不等于文章的 Q4 截图或未附带的网盘工作流**。

文章明确报告旧 `image_z_image_turbo.json` 子图在外部改提示词似乎不生效，进入子图内修改有效；作者怀疑 Nodes 2.0，建议关 Nodes 2.0 并使用平铺完整工作流。这个归因尚未独立复现。后续验证应固定 seed、采样和分辨率，直接修改平铺图的 `CLIPTextEncode` 文本，保存不同输出和对应 API prompt/history；再对相同提示词做 Q4/Q3 比较。每张图单独记录模型 SHA、提示词、输出与视觉判读。文章的一张量化对照图和“6G 挑战”倡议都不能证明这台 8GB VRAM、16GB RAM 机器能稳定生成 1024² 图。

`jayn7` [模型卡](https://huggingface.co/jayn7/Z-Image-Turbo-GGUF)的 Diffusers 示例用 `num_inference_steps=9`、`guidance_scale=0.0`（称 8 次 DiT forward），这与截图里的 ComfyUI `steps=9,cfg=1` 属于不同 API 语义，不应直接按数值等同。先复现文章截图的 ComfyUI 设置，再单变量调整以寻找本机内存边界。
