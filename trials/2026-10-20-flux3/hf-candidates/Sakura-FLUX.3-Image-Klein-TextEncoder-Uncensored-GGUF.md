---
license: apache-2.0
base_model: Qwen/Qwen3-VL-4B-Instruct
base_model_relation: finetune
library_name: gguf
pipeline_tag: text-to-image
tags:
  - sakura
  - sakura-media
  - gguf
  - stable-diffusion.cpp
  - comfyui
  - text-encoder
  - flux
  - flux-3-image-klein
  - qwen3-vl
  - uncensored
  - abliterated
  - not-for-all-audiences
widget:
  - text: "A vast floating harbour city above the clouds at golden hour: huge wooden and brass airships docking at suspended piers, tiny people on the gangways, waterfalls spilling off the edge of a sky island, warm light, epic wide shot, detailed fantasy concept art."
    output:
      url: images/01_airship.png
  - text: "A hand-painted 1980s fantasy film poster: a warrior woman with long braided hair and a glowing sword stands on a cliff facing a gigantic dragon wreathed in flames, storm clouds and a burning castle behind her. The title at the top reads \"EMBER CROWN\" in ornate golden letters, the tagline below says \"One sword. One kingdom.\""
    output:
      url: images/02_emberqueen.png
  - text: "A colossal rusted mecha robot standing motionless in a flooded city at sunrise, moss and flowers growing on its armour, a tiny boat with a child passing between its legs, soft golden mist, epic cinematic wide shot, concept art."
    output:
      url: images/03_mecha.png
  - text: "Anime movie key visual: a mountain village at night during a lantern festival, hundreds of glowing paper lanterns rising into a sky full of stars, a girl in a yukata with a fox mask on her head looking up, warm light, rich detail, painterly background."
    output:
      url: images/04_lanterns.png
  - text: "A narrow rainy street at night in a dense city, neon signs in many colours reflected in the puddles, a lone cyclist holding an umbrella, cinematic wide shot."
    output:
      url: images/05_street.png
  - text: "Portrait photo of an elderly fisherman with a weathered face and a grey beard, wearing a yellow raincoat, a harbour with boats softly out of focus behind him, overcast light."
    output:
      url: images/06_fisherman.png
  - text: "A snow leopard standing alert on a snowy ridge in a light snowfall, head turned toward the camera, both rounded ears upright and clearly visible with black backs and white tufts, thick spotted fur dusted with snow, pale blue eyes, shallow depth of field, wildlife photograph, telephoto lens."
    output:
      url: images/07_leopard.png
  - text: "A clockwork dragon sculpture made of polished brass gears, springs and tiny rivets, wings of thin copper plates, perched on an old wooden workbench, studio macro photograph with dramatic side light and a soft dark background."
    output:
      url: images/08_clockdragon.png
  - text: "A Japanese woodblock print in ukiyo-e style: a samurai cat in armour fishing from a wooden bridge under a huge full moon, ripples on the water, cherry blossom branches, flat colours with fine black outlines, a small red seal in the corner."
    output:
      url: images/09_woodblock.png
---

# Sakura — FLUX.3 Image Klein text encoder, uncensored (GGUF)

**Only the text encoder is uncensored.** This repository contains an abliterated version of the Qwen3-VL-4B-Instruct text encoder that [FLUX.3 Image Klein](https://huggingface.co/black-forest-labs/flux-3-image-klein) uses to read the prompt. It contains **no image model**: use it with the image model files of [Sakura-FLUX.3-Image-Klein-GGUF](https://huggingface.co/webmp3/Sakura-FLUX.3-Image-Klein-GGUF), which we did not change (and which are not uncensored). The encoder is a modified Qwen3-VL-4B-Instruct under **Apache-2.0** (`LICENSE-Apache-2.0.txt`, see `NOTICE`). Independent work, not made or endorsed by Alibaba/Qwen or Black Forest Labs.
For adults only; you are responsible for what you generate and for the laws and licenses that apply to you. The image model is under the FLUX Kommunity License (see its repository).

## Sample generations

<Gallery />

Image model Q8_0 from [Sakura-FLUX.3-Image-Klein-GGUF](https://huggingface.co/webmp3/Sakura-FLUX.3-Image-Klein-GGUF) and **this repository's uncensored text encoder**, ComfyUI 0.41.1 with ComfyUI-GGUF (Radeon 8060S), 1024x1024, 16 steps, CFG 1.0, `euler`/`simple`. These are the **same nine prompts and seeds** (1202, 1302, 1305, 1306, 1105, 1103, 1503, 1506, 1406 in the order shown) as in the repositories [Sakura-Qwen-Image-2.1-Turbo-Uncensored-GGUF](https://huggingface.co/webmp3/Sakura-Qwen-Image-2.1-Turbo-Uncensored-GGUF) and [Sakura-Iris-3B-Uncensored-GGUF](https://huggingface.co/webmp3/Sakura-Iris-3B-Uncensored-GGUF), so that the models can be compared. One seed per prompt, no re-rolls, all nine images are shown; the prompts were chosen for those repositories from a larger set, not for FLUX. The prompts are the captions of the images above. The same prompts and seeds with the official encoder are in the main repository; against those images (same image model, same seeds) the PSNR is 33.4 dB mean / 26.1 dB min over 9 prompts. The FLUX images were made with ComfyUI, the Qwen and Iris images with stable-diffusion.cpp, and models, steps and samplers differ.

The prompts are neutral. These images say nothing about what the edited encoder changes for restricted content; they only show that ordinary prompts still work. No sample images of restricted content are included.

## What to expect

This repository changes only the **text encoder**. The abliteration removes the refusal behaviour of the language model; it does not teach the image model anything, and the image model is not changed. With neutral prompts the images are very similar to those of the official encoder (PSNR 33.4 dB mean / 26.1 dB min over 9 prompts, same image model, same seeds). We have **not** measured the effect on restricted content. If the image model cannot draw something, a different text encoder will not change that.

## What you need to run it

The text encoder is in this repository; the image model and the VAE are in the [main repository](https://huggingface.co/webmp3/Sakura-FLUX.3-Image-Klein-GGUF). Pick the column of the program you use (🟦 stable-diffusion.cpp, 🟧 ComfyUI):

| Part | 🟦 **stable-diffusion.cpp** | 🟧 **ComfyUI** |
|---|---|---|
| Image model | `Sakura-FLUX.3-Image-Klein-Q8_0-5.58GiB.gguf` from the main repository (or another file from there), passed with `--diffusion-model` | the same file, loaded with **UNET Loader (GGUF)** ([ComfyUI-GGUF](https://github.com/city96/ComfyUI-GGUF)) |
| **Uncensored text encoder** | **`Sakura-TextEncoder-Qwen3VL-4B-Uncensored-Q8_0-3.99GiB.gguf`**, passed with `--llm` | **`Sakura-TextEncoder-Qwen3VL-4B-Uncensored-bf16-8.27GiB.safetensors`**, loaded with the normal **Load CLIP** node, type `flux3` |
| VAE | `flux2-vae.safetensors` from the main repository, passed with `--vae` | the same file, loaded with **Load VAE** |
| Program | `sd-cli` of [stable-diffusion.cpp](https://github.com/leejet/stable-diffusion.cpp/releases) release `master-968-8cd731e` or newer (we used commit `8cd731e`, Vulkan build), not included | ComfyUI 0.41.0 or newer (we used 0.41.1) with the ComfyUI-GGUF custom node, not included |

```bash
sd-cli --diffusion-model Sakura-FLUX.3-Image-Klein-Q8_0-5.58GiB.gguf --llm Sakura-TextEncoder-Qwen3VL-4B-Uncensored-Q8_0-3.99GiB.gguf --vae flux2-vae.safetensors -p "your prompt" --cfg-scale 1.0 --steps 16 --sampling-method euler -W 1024 -H 1024 -o out.png
```

ComfyUI: put the encoder (`.safetensors`) into `ComfyUI/models/text_encoders/`, the image model and VAE of the main repository into `diffusion_models/` and `vae/`, install ComfyUI-GGUF, and drag `Sakura-FLUX.3-Image-Klein_ComfyUI_workflow_api.json` into ComfyUI (sampler `euler`, scheduler `simple`, 16 steps, CFG 1.0, 1024x1024, seed 42: exactly what we tested).

Two workflows are included, both set to the settings we tested: `Sakura-FLUX.3-Image-Klein_ComfyUI_workflow_api.json` loads the image model as GGUF (file from the main repository, needs ComfyUI-GGUF) and `Sakura-FLUX.3-Image-Klein_ComfyUI_workflow_api_safetensors.json` uses the standard **UNET Loader** for the official FLUX.3 Klein diffusion model in safetensors format (pick your file in the loader node; we tested the GGUF files, not the safetensors file with this workflow). In both, the image model and the VAE are **not** in this repository; the node titles say where each file comes from.

**Time per image** (1024x1024, 16 steps, Radeon 8060S, nothing else running on the GPU, Q8_0 image model, official text encoder): ComfyUI 40.2 s once the models are loaded (50.2 s for the first image including loading); stable-diffusion.cpp 91.4 s per image as a one-shot `sd-cli` run including model loading. For comparison the BF16 image model took 36.2 s per image in ComfyUI: the GGUF files are smaller but **not faster** here, we did not investigate why.

## What is "uncensored" here, exactly

| Part | What we did |
|---|---|
| **Text encoder** (Qwen3-VL-4B) | The `text_encoder/` of the official FLUX.3 repository is byte-identical (SHA256 of both shards) to `Qwen/Qwen3-VL-4B-Instruct`. We edited it with an abliteration method (settings chosen by us; by the optimisation's own count refusals on its 100 evaluation prompts 97 -> 13, first-token KL divergence 0.163) and made BF16 safetensors (ComfyUI) and GGUF Q8_0, Q6_K, Q5_K_M and Q4_K_M. |
| **Image model** (5.55 B DiT) | **Not part of this repository and not changed by us** (quantized in the main repository from the official weights). We make no claim about how much the image model itself restricts. |

What we did **not** measure: how much the edited encoder changes the *images* for restricted content. The refusal numbers describe the encoder used as a chat model; in this pipeline it only supplies embeddings.

### Text encoder: refusals

Our own measurement with the encoder as a chat model (104 prompts of the test split of `mlabonne/harmful_behaviors`, plain chat, thinking off, temperature 0, 300 tokens, `llama-server` b11594, Q8_0 files unless noted; the first 100 of the 104 are the evaluation prompts the edit was optimized against, so they are **not** held out; strict = English refusal phrases, markers = a broader keyword list):

| Text encoder | strict refusals | broad markers |
|---|---:|---:|
| official, unmodified (Q8_0) | 101 / 104 | 101 / 104 |
| **ours (Q8_0)** | **0 / 104** | 17 / 104 |
| **ours (Q4_K_M)** | 0 / 104 | 18 / 104 |

Quantization loss of our encoder files (KL divergence against our Q8_0, `llama-perplexity` b11594, 20 chunks of 2048 tokens of English and web text):

| Encoder file | KLD en | KLD web | same top token en / web |
|---|---:|---:|---|
| Q6_K | 0.0063 ± 0.0003 | 0.0083 ± 0.0008 | 96.7 / 95.3 % |
| Q5_K_M | 0.0108 ± 0.0005 | 0.0125 ± 0.0010 | 95.6 / 94.2 % |
| Q4_K_M | 0.0315 ± 0.0013 | 0.0317 ± 0.0016 | 92.6 / 91.0 % |

## Files

| File | Size | What it is | 🟦 sd.cpp | 🟧 ComfyUI |
|---|---:|---|---|---|
| `Sakura-TextEncoder-Qwen3VL-4B-Uncensored-Q8_0-3.99GiB.gguf` | 3.99 GiB | **our uncensored text encoder**, GGUF Q8_0 (recommended) | tested | not tested |
| `Sakura-TextEncoder-Qwen3VL-4B-Uncensored-Q6_K-3.08GiB.gguf` | 3.08 GiB | **our uncensored text encoder**, GGUF Q6_K | not tested | not tested |
| `Sakura-TextEncoder-Qwen3VL-4B-Uncensored-Q5_K_M-2.69GiB.gguf` | 2.69 GiB | **our uncensored text encoder**, GGUF Q5_K_M, with importance matrix | not tested | not tested |
| `Sakura-TextEncoder-Qwen3VL-4B-Uncensored-Q4_K_M-2.33GiB.gguf` | 2.33 GiB | **our uncensored text encoder**, GGUF Q4_K_M, with importance matrix | not tested | not tested |
| `Sakura-TextEncoder-Qwen3VL-4B-Uncensored-bf16-8.27GiB.safetensors` | 8.27 GiB | **our uncensored text encoder**, BF16, one file for the ComfyUI `CLIPLoader` (type `flux3`) | not tested | tested |
| `Sakura-FLUX.3-Image-Klein_ComfyUI_workflow_api_safetensors.json` | small | the same workflow with the standard UNET Loader for the official safetensors image model (pick the file yourself) | - | not tested with the safetensors image model |
| `Sakura-FLUX.3-Image-Klein_ComfyUI_workflow_api.json` | small | ComfyUI workflow (API format); loads the image model and VAE of the main repository, the same graph our test runs submitted | - | tested |

The columns say what we actually ran with that file: 🟦 stable-diffusion.cpp = one 1024x1024 image generated with it (the Q8_0 file); 🟧 ComfyUI = the six test images above (the BF16 file). "not tested" means we did not run that file in an image pipeline (the quantization loss of those files is in the table above).

## What we changed

- `Sakura-TextEncoder-Qwen3VL-4B-Uncensored-*`: the official Qwen3-VL-4B-Instruct text encoder with our edit of part of the language weights, converted to GGUF and quantized with llama.cpp, using an importance matrix computed by us on the edited model (English and German text). The BF16 safetensors file is the edited encoder in one file. Modified files.

**Not measured:** how the uncensored encoder behaves with prompts that the official encoder handles worse, image editing with reference images, other languages, speed on other hardware.

## License and use

Apache-2.0 (`LICENSE-Apache-2.0.txt`) as the original Qwen3-VL-4B-Instruct; the files are modified (ablated and quantized), see `NOTICE`. The image model files in the main repository are under the FLUX Kommunity License, which applies to their use and to the generated outputs as that license states.
Part of the **[Sakura Media](https://huggingface.co/collections/webmp3/sakura-media-6acdbccf37881e7c4187470c)** line.

## Credits

- Original text encoder: [Qwen/Qwen3-VL-4B-Instruct](https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct) (Qwen team, Alibaba), used by [black-forest-labs/flux-3-image-klein](https://huggingface.co/black-forest-labs/flux-3-image-klein).
- Conversion and quantization: [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp) (MIT), [leejet/stable-diffusion.cpp](https://github.com/leejet/stable-diffusion.cpp) (MIT); loading: [city96/ComfyUI-GGUF](https://github.com/city96/ComfyUI-GGUF).

---

<details><summary>中文说明 · 樱花 (Simplified Chinese)</summary>

> English above。完整的独立中文版见 [README_zh.md](https://huggingface.co/webmp3/Sakura-FLUX.3-Image-Klein-TextEncoder-Uncensored-GGUF/blob/cd9633fa27922b60ec6c876317e7482adf3baf0f/README_zh.md)。

**只有文本编码器被去审查。** 本仓库包含 [FLUX.3 Image Klein](https://huggingface.co/black-forest-labs/flux-3-image-klein) 用来读取提示词的 Qwen3-VL-4B-Instruct 文本编码器的消融(abliterated)版本。**不包含图像模型**:请配合 [Sakura-FLUX.3-Image-Klein-GGUF](https://huggingface.co/webmp3/Sakura-FLUX.3-Image-Klein-GGUF) 中的图像模型文件使用(我们没有改动图像模型,它也没有被去审查)。编码器是修改过的 Qwen3-VL-4B-Instruct,使用 **Apache-2.0**(`LICENSE-Apache-2.0.txt`,见 `NOTICE`)。属于独立工作,并非 Alibaba/Qwen 或 Black Forest Labs 制作或认可。仅限成年人使用;您需对自己生成的内容以及适用于您的法律和许可证负责。图像模型使用 FLUX Kommunity License(见其仓库)。

## 运行所需文件

| 部分 | 🟦 **stable-diffusion.cpp** | 🟧 **ComfyUI** |
|---|---|---|
| 图像模型 | 主仓库中的 `Sakura-FLUX.3-Image-Klein-Q8_0-5.58GiB.gguf`(或其他文件),通过 `--diffusion-model` 传入 | 同一文件,用 **UNET Loader (GGUF)** 加载 |
| **去审查文本编码器** | **`Sakura-TextEncoder-Qwen3VL-4B-Uncensored-Q8_0-3.99GiB.gguf`**,通过 `--llm` 传入 | **`Sakura-TextEncoder-Qwen3VL-4B-Uncensored-bf16-8.27GiB.safetensors`**,用常规 **Load CLIP** 节点加载,类型 `flux3` |
| VAE | 主仓库中的 `flux2-vae.safetensors`,通过 `--vae` 传入 | 同一文件,用 **Load VAE** 加载 |
| 程序 | stable-diffusion.cpp `master-968-8cd731e` 或更新版本的 `sd-cli`(我们使用 commit `8cd731e`),不包含 | ComfyUI 0.41.0 或更新版本及 ComfyUI-GGUF 自定义节点,不包含 |

## 这里的“去审查”具体指什么

- **文本编码器**:官方 FLUX.3 仓库的 `text_encoder/` 与 `Qwen/Qwen3-VL-4B-Instruct` 逐字节相同(两个分片的 SHA256 均已核对)。我们用消融方法编辑了它(设置由我们选择;按优化过程自己的计数,其 100 条评估提示上的拒绝从 97 降到 13,首个 token 的 KL 散度 0.163),并制作了 BF16 safetensors(ComfyUI)以及 GGUF Q8_0、Q6_K、Q5_K_M、Q4_K_M。
- **图像模型**:不在本仓库中,我们也没有改动;对图像模型本身有多少限制不作任何说明。

## 我们的测量

- **拒绝次数**(把编码器当作聊天模型;`mlabonne/harmful_behaviors` 测试集的 104 条提示,温度 0,300 个 token;其中 100 条正是优化所用的评估提示,因此并非留出数据):官方未改动 **101 / 104**,我们的 **0 / 104**(Q8_0),**0 / 104**(Q4_K_M)。
- 与官方编码器生成的图像(同一图像模型、同样种子,九条提示词)相比,PSNR 为 33.4 dB mean / 26.1 dB min over 9 prompts。没有测量被编辑的编码器在受限内容上对 *图像* 的改变;本仓库不包含受限内容的示例图片。
- **每张图耗时:** 见英文版(只有在 GPU 空闲时的测量才会写入)。
- **没有测量:** 官方编码器处理较差的提示上被编辑编码器的表现、参考图像编辑、其他语言、其他硬件上的速度。

## 许可与致谢

Apache-2.0(与原始 Qwen3-VL-4B-Instruct 相同);文件经过修改(消融并量化),见 `NOTICE`。属于 **[Sakura Media](https://huggingface.co/collections/webmp3/sakura-media-6acdbccf37881e7c4187470c)** 系列。致谢:Qwen / Alibaba(Qwen3-VL-4B-Instruct)、Black Forest Labs、ggml-org/llama.cpp、leejet/stable-diffusion.cpp、city96/ComfyUI-GGUF。

</details>
