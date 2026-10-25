# 刘悦的技术博客：公众号原文核验与模型来源备查

核验日期：2026-10-18，Asia/Shanghai。

**截至本次核验，已读取的微信公众号原文为 0 篇。** 已获取的是搜狗微信的公开索引元数据，以及作者个人博客、B 站视频页面。不能将个人博客日期、视频日期、论坛整理日期填成微信公众号文章的发布日期，也不能声称已经爬取公众号历史文章。

## 公众号索引中实际看到的记录

公开[搜狗微信文章搜索：刘悦的技术博客](https://weixin.sogou.com/weixin?type=2&query=%E5%88%98%E6%82%A6%E7%9A%84%E6%8A%80%E6%9C%AF%E5%8D%9A%E5%AE%A2)返回两条署名精确为“刘悦的技术博客”的记录：

1. **Faster-Qwen3-TTS,流式接口API,实时推理,速度1比0.5,多人对话,智能多音字,4**
   - 搜索索引中的日期：**2026-03-17**。
   - 涉及模型：**Faster-Qwen3-TTS / Qwen3-TTS**，据标题识别。
   - 标题在索引里以“4”结束，属于截断标题；没有补写未看到的部分。
   - 索引 HTML 时间戳：`1773744212`，换算为北京时间 `2026-03-17 18:43:32 +08:00`。这仍是搜索索引的时间字段，未与微信正文核对。

2. **Ming-omni-tts-0.5B,4G显存可用,接口API调用,支持超长文本,情感控制,中英混读**
   - 搜索索引中的日期：**2026-02-25**。
   - 涉及模型：**Ming-omni-tts-0.5B**，据标题识别。
   - 索引 HTML 时间戳：`1772002151`，换算为北京时间 `2026-02-25 14:49:11 +08:00`。未与微信正文核对。

两条均属于语音主题。索引中的“接口 API”不能单独证明是本地服务还是远程商业 API，需要正文或项目来源才能判断。

随后主任务通过浏览器读取[同一搜狗搜索第 2 页](https://weixin.sogou.com/weixin?query=%E5%88%98%E6%82%A6%E7%9A%84%E6%8A%80%E6%9C%AF%E5%8D%9A%E5%AE%A2&type=2&page=2&ie=utf8)，看到以下同名公众号索引记录。以下标题按索引可见部分保留，截断处不补写；“2 天前”“22 小时前”保留原显示，未推算为精确发布日期。模型均仅据标题识别。

3. **Strata-Qwen3.8-Flash-Next-Uncensored,8G显存可用,125B参数**；日期 **2026-10-11**；模型 **Strata / Qwen3.8-Flash-Next-Uncensored**。
4. **Kroma-V0.3.1-Turbo-4步迭代,8G显存可用,多图参考,文生图,图生图(洗图),换头,**；日期显示 **2 天前**；模型 **Kroma V0.3.1 Turbo**。
5. **Moss-Image-5B-Uncensored-8步迭代,8G显存可用,文生图,图生图(洗图),自**；日期显示 **22 小时前**；模型 **Moss-Image-5B-Uncensored**。
6. **Qwen-Image-2.1-Turbo-UN-原生8步迭代,局部重绘,多图参考,8G显存可用,文生**；日期 **2026-10-10**；模型 **Qwen-Image-2.1-Turbo-UN**。
7. **Qwen-Image-2.1-局部重绘,多图参考,8G显存可用,文生图,图生图(洗图),换头换脸,角**；日期 **2026-10-07**；模型 **Qwen-Image-2.1**。

这些记录解决了“索引中是否有该公众号近期 ComfyUI 相关主题”的核验问题，仍不意味着已获取微信正文、完整标题、模型清单或权重下载地址。搜索结果中的型号后缀也可能是整合包/工作流名称，未与模型作者的仓库逐项确认。

本次获取搜狗结果页成功；继续打开搜狗结果链接时，HTTP 返回 `302` 并转向 `/antispider/`。主任务在浏览器里也观察到微信原文访问被策略拒绝。因此没有尝试绕过限制读取原文。搜狗“公众号搜索”没有返回官方认证订阅号，也不等于这个公众号不存在或没有文章。

## 已核实的作者其他平台内容

以下是**其他平台的记录，不是公众号文章清单**。日期只对应链接所在页面。标题较长时使用保留模型名称的简称；点击可看完整标题。

1. **2025-11-27，B 站视频**：[Z-Image-Turbo：文生图、图生图、自动提示词、基于 ComfyUI](https://www.bilibili.com/video/BV15XSuBkEmb/)。模型：Z-Image-Turbo；标题还提到 Qwen3-VL 自动提示词。
2. **2026-01-01，B 站视频**：[Qwen-Image-2512-GGUF：文生图、反推提示词](https://www.bilibili.com/video/BV1DRvUBkEdi/)。模型：Qwen-Image-2512，GGUF 量化。
3. **2026-01-18，B 站视频**：[Flux.2-Klein-9B-GGUF：局部重绘、文生图、多图编辑](https://www.bilibili.com/video/BV1VwkWBtE5r/)。模型：FLUX.2 Klein 9B，GGUF 量化。
4. **2026-05-12，B 站视频**：[LongCat-Image-Edit-Turbo：文生图、图生图、局部重绘](https://www.bilibili.com/list/3031494?bvid=BV1JT5u68Ead&oid=116561956312155)。模型：LongCat-Image-Edit-Turbo。
5. **2026-01-19，B 站视频**：[LTX-2-distilled：图片数字人、8 步采样](https://www.bilibili.com/video/BV1FwkuBwEXk/)。模型：LTX-2 distilled。
6. **2025-11-05，B 站视频**：[Wan2.2-Lightx2v-Distill-GGUF：图生视频、首尾帧、4 步采样](https://www.bilibili.com/video/BV18r14BuEeL/)。模型：Wan2.2 + Lightx2v 蒸馏/GGUF。
7. **2024-12-09，个人博客**：[m4 mac mini 本地部署 ComfyUI，测试 Flux-dev-GGUF](https://v3u.cn/a_id_370)。文中列出 `flux1-dev-Q4_1.gguf` 与 `t5-v1_1-xxl-encoder-Q5_K_M.gguf`。该实验平台是 Mac/MPS。
8. **2024-12-08，个人博客**：[使用腾讯混元 HunyuanVideo 的 FP8 量化版本](https://v3u.cn/a_id_369)。文中给出 HunyuanVideo FP8、VAE、LLaVA-Llama-3-8B 文本编码器与 CLIP 来源；实验设备是 RTX 4060 Laptop 8GB。

作者个人站[首页](https://v3u.cn/)和以上文章页均展示“刘悦的技术博客公众号”二维码。它可以支持作者站点与公众号品牌之间的关联，不能证明每个站外条目在公众号发布过。

## 前期模型核验结果，仅供之后继续试机

这一节是模型项目来源，不构成公众号文章核验结果，也不代表本机运行成功。本研究没有安装软件或下载模型权重。

- **Z-Image-Turbo** 有公开本地权重和 ComfyUI 原生工作流。[官方模型项目](https://github.com/Tongyi-MAI/Z-Image)；[ComfyUI 官方指南](https://docs.comfy.org/tutorials/image/z-image/z-image-turbo)。官方指南列出扩散主模型、Qwen3-4B 编码器和 `ae.safetensors` 三类文件。
- 若继续按低显存路线试验，[Unsloth 的 Z-Image-Turbo 量化仓库](https://huggingface.co/unsloth/Z-Image-Turbo-GGUF/tree/main)列出 `z-image-turbo-Q4_K_M.gguf` 为约 **5.02 GB**；[Qwen3-4B 量化仓库](https://huggingface.co/unsloth/Qwen3-4B-GGUF/tree/main)列出 `Qwen3-4B-Q4_K_M.gguf` 为约 **2.50 GB**。这些是第三方量化制品；文件体积不等于运行时显存。
- GGUF 插件维护者明确解释：Z-Image 的编码器是原版 **Qwen3-4B**，不是 Qwen3-VL-4B；维护者给出了 Unsloth 量化来源。[ComfyUI-GGUF 维护者说明](https://github.com/city96/ComfyUI-GGUF/issues/368)。视频里的 Qwen3-VL 自动提示词是额外功能，不能拿来替换基础文本编码器。
- [MOSS-Image 官方项目](https://github.com/OpenMOSS/MOSS-Image)于 **2026-10-16**宣布 Base/SFT 权重，主干为 5B，并提供 ComfyUI 插件；[插件说明](https://raw.githubusercontent.com/OpenMOSS/MOSS-Image/main/comfyui/moss-image/README.md)要求完整的 transformer、text_encoder、tokenizer、vae 目录。仅凭“5B”不足以判断整套比 Z-Image 更省内存。社区中找到的视频线索尚未核实其第一方页面日期，因此没有把它加入上面的已核实条目。
- 作者标题中的“8G 显存可用”“支持 50 系”不证明 RX 6650 XT 能复现。尤其不要把文中的 CUDA PyTorch 安装命令覆盖到现有 AMD 环境；[其 HunyuanVideo 原文](https://v3u.cn/a_id_369)明确使用 CUDA wheel 和 RTX 4060 Laptop。[上游 SageAttention 的构建代码](https://github.com/thu-ml/SageAttention/blob/main/setup.py)列出 NVIDIA 架构及 CUDA 编译要求，不能默认当作本机 AMD 加速插件。

下一步应先取得能够核验账号、标题、发布日期和正文的具体公众号文章链接，或继续将公开搜索索引明确标为“索引记录”。确认用户关心的条目后，再逐个核对权重、依赖和本机运行结果。
