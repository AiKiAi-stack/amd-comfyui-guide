# Flux.3-5.6B-UN：Hugging Face 同版检索

检查日期：2026-10-20。用户要求找同名版本，停止标准版替代测试。

## 当前结论

没有找到能够确认对应刘悦 `Flux.3-5.6B-UN` 整合包的公开 Hugging Face 仓库或文件。精确名称 `Flux.3-5.6B-UN` 和 `Flux.3-Image-5.6B-UN` 的 HF models API 搜索返回空列表。扩大到 flux3、flux-3、Sakura-FLUX.3、Uncensored 等别名后可找到组件候选，但没有作者、文件名、哈希或工作流证据将其对应到该整合包。搜索未命中不等于该版本不存在。

## 相关候选及差异

- [webmp3/Sakura-FLUX.3-Image-Klein-TextEncoder-Uncensored-GGUF](https://huggingface.co/webmp3/Sakura-FLUX.3-Image-Klein-TextEncoder-Uncensored-GGUF)：修改的是 Qwen3-VL-4B 文本编码器，模型卡明确图像模型没有去审查改动。其展示的 ComfyUI 流程为 16 步，不是作者四步 UN 整合包。仓库 commit `cd9633fa27922b60ec6c876317e7482adf3baf0f`。
- [webmp3/Sakura-FLUX.3-Image-Klein-GGUF](https://huggingface.co/webmp3/Sakura-FLUX.3-Image-Klein-GGUF)：标准蒸馏图像模型的社区量化，模型卡为 16 步，不能仅凭与上述 encoder 组合就判定为作者同版。commit `02c8b1edfc3159a39e7443a9c94e283b7d1b7f3e`。
- [Muinez/flux3-klein-distil-4step](https://huggingface.co/Muinez/flux3-klein-distil-4step)：独立四步蒸馏 LoRA 候选，HF 元数据关联 Klein **base**，未声明 UN 或刘悦整合包来源。不能直接假定适配已下载的 `_sd_` 蒸馏主干。详见本目录四步候选报告。
- [pottokao/FLUX.3-Klein-Text-Encoder-Heretic-DHQ-GGUF](https://huggingface.co/pottokao/FLUX.3-Klein-Text-Encoder-Heretic-DHQ-GGUF)：另一独立修改文本编码器，未发现与作者整合包的映射证据。commit `2d87f23da080416e74b05db8c772186eb2b29e2c`。

## 本机实际状态

此前用户允许从 ModelScope 下载时，标准 Klein INT8 diffusion、Qwen3VL INT8 encoder、Flux2 VAE 及两个小工作流均已下载并通过字节数和 SHA-256 校验。它们不是作者同版证明。用户随后要求停止；试验服务器已停止，尚未提交 FLUX3 推理任务，没有 FLUX3 输出图片。保留已下载文件，未擅自删除。

本次 Hugging Face 检索仅获取 API 元数据与模型卡文本，没有下载任何候选权重，也没有拼装候选组件运行测试。作者版继续 pending，需作者包内部权重/工作流清单或可核对的同版来源。

## 第二个链接的工作流

[作者 Compshare 镜像页](https://www.compshare.cn/images/uc0UnUzrIbtD) 可访问，但未找到公开工作流下载；三个示例 PNG 没有标准 ComfyUI prompt/workflow 元数据。镜像内部是否包含工作流仍未知。检查记录见 `flux3-author-workflow-access-2026-10-20.md`。

## 原始证据

- `trials/2026-10-20-flux3/hf-search.json`：初始精确名称与同家族搜索。
- `trials/2026-10-20-flux3/hf-candidates/exact-alias-search.json`：精确名称变体和 UN 别名搜索；模糊搜索也包含不相关结果，未将其视为命中。
- `trials/2026-10-20-flux3/hf-candidates/`：三个候选的 API 元数据与原始模型卡。
- `trials/2026-10-20-flux3/*.verified.json`：此前标准版下载校验收据。
