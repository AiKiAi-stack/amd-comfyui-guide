# 五组 ComfyUI 文章功能声明核对

核验日期：2026-10-19。它不代表正在进行的本机功能试跑的最终状态。试跑进度与结果见[2026-10-19 功能试验记录](../trials/2026-10-19-features/)。搜狗标题和相对日期照录自[索引核验记录](./liuyue-comfyui-models-2026-10-18.md)；不补写任何截断尾部。

## 证据等级

- **I｜公众号索引**：搜狗可见的标题和日期；只能证明索引收录了这些字样，不能替代正文。
- **A｜作者站外视频记录**：bbs.monster 的公开视频摘要页带有“刘悦的技术博客”作者标注和 B 站播放器。只确认页面明确描述或画面展示的内容；论坛日期不是公众号发布日期，入口按钮也不等于完整任务验证。
- **M｜模型方文档**：模型作者或 ComfyUI 官方说明模型/官方工作流的能力；不能自动证明刘悦文章使用了该版本或该工作流。
- **W｜额外工作流/适配器**：第三方 LoRA、节点或组合流程。该能力应归属于这一套流程，不能说成基础权重单独具备。
- **T｜本机试验记录**：本机 ComfyUI 的任务历史、日志与输出图；只证明记录中的权重和具体参数组合，不自动证明文章所用整合包相同。

在 v3u.cn 未检索到这五组的对应作者文章；B 站精确标题检索也未找到可独立核对的五条原视频页面。BBS 记录嵌有作者 B 站播放器并标注作者账号，以下将其记作作者视频的站外记录，不把论坛日期当成 B 站或公众号的原始发布日期。微信公众号原文此前被浏览器安全策略拒绝；本次没有尝试绕过该策略。

## 1. Kroma V0.3.1 Turbo

**索引可见声明（I）**：`Kroma-V0.3.1-Turbo-4步迭代,8G显存可用,多图参考,文生图,图生图(洗图),换头,`。标题以逗号结束，保留原样。

作者站外条目《[Kroma V0.3.1 Turbo：文生图启动与ComfyUI入口](https://bbs.monster/thread-5308-1-1.html)》（BBS 显示 2026-10-17）展示默认文生图界面、尺寸/迭代设置和输出。页面把“4步迭代、8G显存可用”记为原视频标题说法；没有独立验证显存或速度。它还明确说本段只讲基本文生图入口，多图参考和图生图完整操作要看其他演示，因此不能据这一条确认索引列出的全部功能。

模型方 [Kroma 卡片](https://huggingface.co/lodestones/Kroma?not-for-all-audiences=true)把其所列版本标作 Text-to-Image，建议 **8–12 步、CFG 1.0–1.5、shift 1.15**，并要求 Krea 2 文本编码器（CLIP 类型 `krea2`）和 VAE。本机试跑的文件是 `kroma-v0.3.1-turbo-opd-Q2_K.gguf`；现有卡片与 OPD 量化变体的对应关系、以及该 OPD 文件自己的推荐设置尚待核对，因此不能据此判定索引所写“4步”与本机这次 4 步测试冲突，也不能把该设置推广到其他 Kroma 变体。[Krea 2 官方说明](https://github.com/krea-ai/krea-2)把 Turbo 的 8 步用于文生图，但不足以单独确定此 OPD 文件的推荐步数。Krea 技术报告确有一套多图**风格参考**系统，但这是 Krea 2 系统能力；Kroma 的公开本地卡片只给出空 latent 的文生图图，未证明当前 Kroma 单文件图已经接入该参考模块，更未证明多图内容编辑或换头。

本机有 `kroma-v0.3.1-turbo-opd-Q2_K.gguf`、`qwen3vl_4b_fp8_scaled.safetensors` 和 `qwen_image_vae.safetensors`，且装有 ComfyUI-GGUF；因此**可先用现有文件尝试基础文生图**。索引中的多图参考、图生图、换头尚无对应 Kroma 工作流/LoRA 在本机文件清单中；换头至少要额外的身份/编辑流程，不能从 Kroma 权重本身推出。第三方 BFS 仓库另有 Krea 2 专用 LoRA/指南（见[BFS 模型卡](https://huggingface.co/Alissonerdx/BFS-Best-Face-Swap)），这是额外适配器线索，不是作者该条视频使用它的证据。

## 2. MOSS-Image-5B

**索引可见声明（I）**：`Moss-Image-5B-Uncensored-8步迭代,8G显存可用,文生图,图生图(洗图),自`。尾部只有“自”，不扩写。

作者站外条目《[Moss-Image-5B整合包：8步文生图与图生图入口](https://bbs.monster/thread-5312-1-1.html)》（BBS 显示 2026-10-18）具体展示默认文生图、8 步、约 7.7/8.0GB 专用显存，以及图生图开关和输入图区域。它支持“作者的整合包在该次 4060 演示中有这些入口/设置”，不等于所有硬件均可在 8GB 运行；页面也没有展开节点安装、图生图参数或自动提示词/批量流程。索引的“自…”仍不可判定。

[OpenMOSS 官方 ComfyUI 说明](https://github.com/OpenMOSS/MOSS-Image/blob/main/comfyui/README.md)给出的是本地模型目录加载和以空 latent 生成的文生图工作流，示例为 50 步、CFG 3、shift 5；它没有展示本文标题所说的图生图入口。OpenMOSS 自有 `moss-image` HFLoader 是一种加载路径；本机 ComfyUI 的核心 `UNETLoader` + `CLIPLoader`（CLIP 类型 `moss_image`）也能加载，HFLoader 插件不是必需节点。8 步来自第三方 [MOSS SFT DMD LoRA](https://huggingface.co/lodestones/MOSS-Image-SFT-8-steps-dmd)，不是 OpenMOSS 官方 Base/SFT 的默认步数。“Uncensored”也没有在 OpenMOSS 官方仓库中对应一个已确认的独立官方权重名。

本机已有 `moss_image_sft_int8_convrot.safetensors`、`qwen3.5_9b_w4a8_gptq.safetensors`、`flux2-vae_small.safetensors` 和 `moss-image-sft-8-steps-dmd-lora.safetensors`。依据[本机试验记录](../trials/2026-10-18/README.md)，已用原生 `UNETLoader` + `CLIPLoader(moss_image)` 加载，并在 gfx1032 INT8 fallback 下完成 512×512、50 步 SFT 出图及 8 步 DMD LoRA 候选出图，均有输出与视觉检查记录（T）。因此 MOSS **可用现有权重和核心节点测试，且上述两组已实测成功**；缺少 OpenMOSS 自有 HFLoader 只代表少了一种可选加载途径。图生图仍只有作者整合包层面的入口证据，本机这次没有验证图生图，也不能把它说成官方基础流程已证实能力。

## 3. Qwen-Image-2.1-Turbo-UN

**索引可见声明（I）**：`Qwen-Image-2.1-Turbo-UN-原生8步迭代,局部重绘,多图参考,8G显存可用,文生`。末尾“文生”截断，不补完。

作者站外条目《[Qwen-Image 2.1 Turbo-UN：8步生成与图像编辑入口](https://bbs.monster/thread-5262-1-1.html)》（BBS 显示 2026-10-11）展示了默认文生图、8 次迭代、参考图上传区，以及局部重绘、角色替换、图生图和姿态控制入口；作者还在画面中提到 4060 笔记本约 6GB 显存。页面说明短片没有逐个展开这些功能，故入口/菜单可见不等于逐项验证成功。此为 uncensored 整合界面展示，不是公众号正文。

上游 [Qwen-Image-2.1-Turbo 模型卡](https://huggingface.co/Qwen/Qwen-Image-2.1-Turbo)确认 Turbo 是 8 步模型，支持文生图与图像编辑，并展示单图转换、多参考构图；[Qwen 2.1 官方说明](https://qwen.ai/blog?id=qwen-image-2.1)还说明基础模型的局部编辑与最多 10 张参考图。它们证明 Qwen 2.1 家族能力，不证明自定义 `UN/Uncensored` 权重与所有界面开关完全等同。8GB 是作者整合包的硬件主张；目前可找到的是单次 4060 约 6GB 画面/说明，不能推成 RX 6650 XT 上的保证。

本机有 `qwen-image-2.1-turbo-Q4_K_M.gguf`、`Qwen-Image-2.1-Turbo-Uncensored-Q4_K.gguf`、`mmproj-Qwen-Image-2.1-Turbo-Uncensored-F16.gguf` 和 `qwen_image_2.1_vae_bf16.safetensors`；ComfyUI-GGUF 已安装。已有这些文件只表示具备尝试条件，不等于 Turbo-UN 组合已运行通过：本机试跑记录中，普通 Turbo 配合原编码器完成了 8 步出图；Turbo-UN 编码器组合则在 GGUF 编码器卸载时触发 Windows native access violation，未生成图片（见[试跑记录](../trials/2026-10-18/README.md)）。局部重绘、多图和角色替换也不能仅凭文件清单算作已验证。不能把这些文件标成与作者整合包相同版本。

## 4. Qwen-Image-2.1

**索引可见声明（I）**：`Qwen-Image-2.1-局部重绘,多图参考,8G显存可用,文生图,图生图(洗图),换头换脸,角`。尾部“角”不扩写。

与索引条目不同，作者较早的站外视频记录《[Qwen-Image-2.1一键角色替换：优化生成速度，8G VRAM可用，文生图/洗图/编辑/批量任务](https://bbs.monster/thread-5206-1-1.html)》（2026-09-29）明确描述了文生图、洗图、图像/多图编辑、角色替换、自动提示词和批量任务。它是同作者、同模型家族的另一条公开记录，可作为作者工作流主张的旁证，不能当成 10 月 7 日公众号原文或用来补全“角…”。其硬件部分是作者对 4060 笔记本的演示/口述，不构成跨 GPU 保证。

[Qwen 官方模型卡/代码](https://github.com/QwenLM/Qwen-Image-2.1)确认基础模型支持文生图与图像编辑；[官方产品说明](https://qwen.ai/blog?id=qwen-image-2.1)列出最多 10 张参考图和局部编辑。这里的“局部编辑”不自动等于特定遮罩式 inpainting 工作流。另有第三方 [BFS Qwen 2.1 头部替换 LoRA 与工作流](https://huggingface.co/Alissonerdx/BFS-Best-Face-Swap/blob/main/docs/qwen-image-2.1.md)，该**专用 BFS 方案**要求匹配 Qwen 2.1 主模型、文本编码器、VAE、两张图的固定输入顺序和专用 LoRA。普通双图参考/图像编辑路径可以先用于尝试换头或角色替换，不等同于复现 BFS 专用方案；结果需按本机试跑记录确认，不能笼统说所有换头都需要专用 LoRA。

本机已有 `qwen-image-2.1-Q4_K_M.gguf`、`qwen3vl_8b_w4a8.safetensors` 和 `qwen_image_2.1_vae_bf16.safetensors`，且有 GGUF 加载插件；**可用现成文件先试普通文生图/图像编辑/多参考工作流**。`loras` 目录没有 BFS 头部替换 LoRA，因而不能用当前权重清单复现该第三方专用换头方案。作者自有整合工作流也未安装在当前 ComfyUI。

## 对本机试机的判断

- **现有权重可测试/已有实测**：Qwen-Image-2.1-Turbo-UN 家族和 Qwen-Image-2.1 基础图像任务有主模型、编码器和 VAE 文件；Kroma 有 Q2、编码器、VAE，可试文生图。MOSS 的本机 50 步 SFT 与 8 步 DMD LoRA 已由核心加载节点出图成功（T）；OpenMOSS HFLoader 插件是可选加载路径。
- **标题不应直接当模型保证**：Kroma 索引的“4步”与本机 OPD Q2_K 试跑使用的 4 步相符；其他 Kroma 变体的推荐设置以及该 OPD 变体与模型卡的对应关系尚待核对。所有“8G 可用”说法都应写成作者对具体整合包/设备的展示或索引声明，而不是对当前 AMD 设备的实测结论。`洗图`、`换头`、`目标替换`等功能词需绑定具体工作流、适配器、输入顺序和参数后再测试。
