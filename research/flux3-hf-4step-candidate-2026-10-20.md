# Hugging Face 的 FLUX3 Klein 4 步 LoRA 候选核验

核验日期：2026-10-20。范围：只读读取 Hugging Face 模型卡、固定 revision 的 README 与仓库文件元数据，并与 BFL 官方 base/distilled 模型卡及作者 Compshare 页面声明对照。本轮没有下载 LoRA 或模型权重、没有运行 GPU，也没有改动推理环境。

## 结论

[`Muinez/flux3-klein-distil-4step`](https://huggingface.co/Muinez/flux3-klein-distil-4step) 是一个 ComfyUI 格式的 **4 步蒸馏 LoRA** 候选。它不是完整 checkpoint；作者说明通过 `LoraLoaderModelOnly` 加载，并明确把适配底模写为 `black-forest-labs/flux-3-image-klein-base`。该 LoRA 的模型卡将其标为实验性短训首版，并说效果可能较粗糙。

它**不是已证实的 `Flux.3-5.6B-UN` 权重或作者同版 LoRA**。模型卡、HF 元数据和版本文件没有提及 `UN`、刘悦、Compshare 或其整合包；精确检索也没有找到两者之间的作者说明或权重映射。因此最多能说它是“FLUX3 Klein 家族的独立 4 步 LoRA 候选”，不能据此认定它复现作者包、支持作者所说功能，或解释作者包中的 `UN`。

### 仓库与文件身份

| 字段 | 核验值 |
|---|---|
| 仓库 | [`Muinez/flux3-klein-distil-4step`](https://huggingface.co/Muinez/flux3-klein-distil-4step) |
| 固定 repo revision | `56905ed03885e46d4e21e0313df144d4f85a244a` |
| HF `lastModified` | `2026-10-15T18:39:05Z` |
| HF tags 中声明的 base | `black-forest-labs/flux-3-image-klein-base` |
| 唯一模型权重文件 | `flux3-klein-distil-4step.safetensors` |
| HF API 文件大小 | 168,765,940 bytes |
| HF LFS SHA-256 元数据 | `63c16535f315818c3ef92c7022ab2337f687e252a008c42a5f3beff82a999e93` |

SHA-256 和字节数来自该 revision 的 Hugging Face API 元数据；本轮没有下载文件进行本地哈希复验。仓库其他文件为 README、LICENSE、NOTICE 和 `.gitattributes`。文件的 [revision 固定链接](https://huggingface.co/Muinez/flux3-klein-distil-4step/tree/56905ed03885e46d4e21e0313df144d4f85a244a)便于复核。

### LoRA 卡片给出的配方

固定 revision 的 [README](https://huggingface.co/Muinez/flux3-klein-distil-4step/blob/56905ed03885e46d4e21e0313df144d4f85a244a/README.md) 明确写的是：

- 适配 **FLUX.3 Image Klein base**，声称 2–4 步工作，4 步为推荐设置，2–3 步也可用。
- CFG 设为 1，不使用 negative prompt。
- `ModelSamplingFlux` 的 `max_shift` 和 `base_shift` 设为 `1.0986`（卡片解释为 `ln 3`）。
- `euler` sampler、`simple` scheduler、LoRA strength `1.0`。
- 训练分辨率为 1024²；卡片称其他分辨率及长宽比也可用。
- 卡片自称 experimental、只短暂训练过，提醒可能有粗糙表现；并说明这不是 BFL 官方模型。

这些是 LoRA 发布者的配方声明，不是本机测试结果，也不是作者 Compshare 整合包的参数确认。

### 与官方 Klein 版本及作者包的关系

[BFL 官方 base 卡](https://huggingface.co/black-forest-labs/flux-3-image-klein-base)将 base 描述为未蒸馏权重，面向微调、LoRA 训练和研究；其表列参考设置为 50 步、guidance 3.5。BFL 把蒸馏版单独放在 [`black-forest-labs/flux-3-image-klein`](https://huggingface.co/black-forest-labs/flux-3-image-klein)，用途是生成和编辑，卡片表列 16 步、无 guidance。Muinez 的 base 声明因此指向官方 **base**，不是官方 **distilled** 主干。

本机已下载校验的 ModelScope 候选则是 [`junwenlu/flux-3-image-klein-ComfyUI`](https://www.modelscope.cn/models/junwenlu/flux-3-image-klein-ComfyUI) 的标准 Klein **INT8 distilled** 主干；具体文件、revision 和 hash 见[此前选择记录](flux3-modelscope-selection-2026-10-20.md)及 `trials/2026-10-20-flux3/selection.json`。它与本 LoRA 声明的 base 不是同一权重。没有找到 Muinez 说明该 LoRA 可直接加载到 distilled checkpoint 的证据，所以不能把这个 LoRA 直接附到已下载的 distilled INT8 主干上并称为匹配配方；也不能仅凭不同 checkpoint 名称断言绝对不兼容。

作者的[Compshare 镜像](https://www.compshare.cn/images/uc0UnUzrIbtD)页面标题为 `Flux.3-5.6B-UN`，另有作者所列 4 步等功能声明，但公开页面没有列出主干文件名、LoRA 文件名、权重哈希或上游映射。本次没有找到该页面与 Muinez LoRA 的可验证连接。两处都出现“4 步”只能说明采样步数声明相似，不能证明同一权重或同一整合包。

## 对本机候选的实际含义

若以后要验证这个 HF LoRA，需要明确测试的是“官方未蒸馏 Klein base + Muinez 4 步 LoRA”这套独立组合，并单独确认 base 权重版本、ComfyUI 加载链和所需显存/内存。它不能替代当前已下载的标准 distilled INT8 主干，也不能算 `Flux.3-5.6B-UN` 的确认测试。本任务依照指示暂停实际下载与 GPU 测试，因此没有给出本机可运行结论。

## 可复核来源与限制

- [Muinez HF 模型卡](https://huggingface.co/Muinez/flux3-klein-distil-4step)；[固定 revision README](https://huggingface.co/Muinez/flux3-klein-distil-4step/blob/56905ed03885e46d4e21e0313df144d4f85a244a/README.md)；[固定 revision 文件树](https://huggingface.co/Muinez/flux3-klein-distil-4step/tree/56905ed03885e46d4e21e0313df144d4f85a244a)。
- [Hugging Face 模型元数据 API](https://huggingface.co/api/models/Muinez/flux3-klein-distil-4step?blobs=true)：用于确认 repo revision、更新时间、tags、模型文件大小与 LFS SHA-256；没有请求 safetensors 权重内容。
- [BFL Klein base 模型卡](https://huggingface.co/black-forest-labs/flux-3-image-klein-base)和[官方 distilled 模型卡](https://huggingface.co/black-forest-labs/flux-3-image-klein)：用于区分两个官方 checkpoint 的用途和参考步数。
- [作者 Compshare 镜像](https://www.compshare.cn/images/uc0UnUzrIbtD)：用于核对作者包公开标题和其未提供权重映射的边界。

本轮再次调用网页正文读取器时，Muinez 页面返回不可访问；上述卡片细节来自固定 revision 的公开 README/API 响应（只读文本与元数据）。没有访问、下载或检查二进制权重。
