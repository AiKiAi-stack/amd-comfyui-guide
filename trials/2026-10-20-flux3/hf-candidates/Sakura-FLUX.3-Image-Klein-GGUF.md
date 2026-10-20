---
license: other
license_name: flux-kommunity-license
license_link: LICENSE.md
base_model: black-forest-labs/flux-3-image-klein
base_model_relation: quantized
library_name: gguf
pipeline_tag: text-to-image
tags:
  - sakura
  - sakura-media
  - gguf
  - stable-diffusion.cpp
  - comfyui
  - text-to-image
  - flux
  - flux-3
  - flux-3-image-klein
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

# Sakura — FLUX.3 Image Klein (GGUF)

**Built with FLUX.** Community quantization of [FLUX.3 Image Klein](https://huggingface.co/black-forest-labs/flux-3-image-klein) (distilled, 16 steps, no CFG) with the official, unmodified Qwen3-VL-4B-Instruct text encoder. Independent work, not made, reviewed or endorsed by Black Forest Labs.
The image model files, the VAE and the workflow are under the **FLUX Kommunity License** (copy in `LICENSE.md`: non-commercial use, or commercial use of outputs only as a Qualifying User under US$5 million revenue with the filtering or review the license requires); the unmodified text encoder is Apache-2.0 (`LICENSE-Apache-2.0.txt`). See `NOTICE`.
An uncensored version of the **text encoder** (only the encoder, the image model is not changed) is available separately: [Sakura-FLUX.3-Image-Klein-TextEncoder-Uncensored-GGUF](https://huggingface.co/webmp3/Sakura-FLUX.3-Image-Klein-TextEncoder-Uncensored-GGUF). It works with the image model files of this repository.

## Sample generations

<Gallery />

Q8_0 image model and the official text encoder, ComfyUI 0.41.1 with ComfyUI-GGUF (Radeon 8060S), 1024x1024, 16 steps, CFG 1.0, `euler`/`simple`. These are the **same nine prompts and seeds** (1202, 1302, 1305, 1306, 1105, 1103, 1503, 1506, 1406 in the order shown) as in the repositories [Sakura-Qwen-Image-2.1-Turbo-GGUF](https://huggingface.co/webmp3/Sakura-Qwen-Image-2.1-Turbo-GGUF) and [Sakura-Iris-3B-GGUF](https://huggingface.co/webmp3/Sakura-Iris-3B-GGUF), so that the models can be compared. One seed per prompt, no re-rolls, all nine images are shown; the prompts were chosen for those repositories from a larger set, not for FLUX. The prompts are the captions of the images above. The same prompts and seeds with our uncensored text encoder are in [Sakura-FLUX.3-Image-Klein-TextEncoder-Uncensored-GGUF](https://huggingface.co/webmp3/Sakura-FLUX.3-Image-Klein-TextEncoder-Uncensored-GGUF). The FLUX images were made with ComfyUI, the Qwen and Iris images with stable-diffusion.cpp, and models, steps and samplers differ, so differences between the sets are not only differences of the text encoder.

## What you need to run it

Everything except the runtime is in this repository. Pick the column of the program you use (🟦 stable-diffusion.cpp, 🟧 ComfyUI):

| Part | 🟦 **stable-diffusion.cpp** | 🟧 **ComfyUI** |
|---|---|---|
| Image model (pick one) | `Sakura-FLUX.3-Image-Klein-Q8_0-5.58GiB.gguf` (best) or a smaller K-quant from the table below, passed with `--diffusion-model` | the same file, loaded with **UNET Loader (GGUF)** ([ComfyUI-GGUF](https://github.com/city96/ComfyUI-GGUF)) |
| Text encoder | `Sakura-TextEncoder-Qwen3VL-4B-Instruct-8bit-3.99GiB.gguf`, passed with `--llm` | `Qwen3-VL-4B-Instruct-bf16-8.27GiB.safetensors`, loaded with the normal **Load CLIP** node, type `flux3` |
| VAE | `flux2-vae.safetensors`, passed with `--vae` | the same file, loaded with **Load VAE** |
| Program | `sd-cli` of [stable-diffusion.cpp](https://github.com/leejet/stable-diffusion.cpp/releases) release `master-968-8cd731e` or newer (we used commit `8cd731e`, Vulkan build), not included | ComfyUI 0.41.0 or newer (we used 0.41.1) with the ComfyUI-GGUF custom node, not included |

The `8bit` in the text-encoder file name is Q8_0; the Q5_K and Q4_K image-model files carry the standard labels `Q5_K_M` / `Q4_K_M` in their names so that the Hub recognises them (they are the uniform Q5_K / Q4_K recipes of stable-diffusion.cpp).

## Install in ComfyUI

1. Put the image model (`.gguf`) into `ComfyUI/models/diffusion_models/`, the VAE into `ComfyUI/models/vae/` and the text encoder (`.safetensors`) into `ComfyUI/models/text_encoders/`.
2. Install [ComfyUI-GGUF](https://github.com/city96/ComfyUI-GGUF) (restart ComfyUI afterwards). The GGUF files carry the metadata key `general.architecture = flux` that its loader needs.
3. Drag `Sakura-FLUX.3-Image-Klein_ComfyUI_workflow_api.json` into ComfyUI (or load it with the "Load" button): **UNET Loader (GGUF)** → KSampler, **Load CLIP** (type `flux3`), **Load VAE**, `EmptyFlux2LatentImage`; sampler `euler`, scheduler `simple`, 16 steps, CFG 1.0 (the workflow is set to exactly what we tested: 1024x1024, seed 42).
4. If you use the official FLUX.3 Klein diffusion model as safetensors instead of a GGUF file, load `Sakura-FLUX.3-Image-Klein_ComfyUI_workflow_api_safetensors.json` (standard **UNET Loader**, pick your file in that node); we tested the GGUF files, not the safetensors file with this workflow.

## Run with stable-diffusion.cpp

```bash
sd-cli --diffusion-model Sakura-FLUX.3-Image-Klein-Q8_0-5.58GiB.gguf --llm Sakura-TextEncoder-Qwen3VL-4B-Instruct-8bit-3.99GiB.gguf --vae flux2-vae.safetensors -p "your prompt" --cfg-scale 1.0 --steps 16 --sampling-method euler -W 1024 -H 1024 -o out.png
```

## Files

| File | Size | What it is | 🟦 sd.cpp | 🟧 ComfyUI | PSNR vs BF16 (mean / min of 6) |
|---|---:|---|---|---|---|
| `Sakura-FLUX.3-Image-Klein-Q8_0-5.58GiB.gguf` | 5.58 GiB | image model (DiT), Q8_0 | tested | tested | 35.1 / 22.8 dB |
| `Sakura-FLUX.3-Image-Klein-Q6_K-4.35GiB.gguf` | 4.35 GiB | image model (DiT), Q6_K, without importance matrix | tested | tested | 28.0 / 17.2 dB |
| `Sakura-FLUX.3-Image-Klein-Q5_K_M-3.68GiB.gguf` | 3.68 GiB | image model (DiT), Q5_K (uniform sd.cpp K-quant recipe; the file name carries the standard label Q5_K_M so the Hub recognises it), with importance matrix | tested | tested | 27.9 / 21.0 dB |
| `Sakura-FLUX.3-Image-Klein-Q4_K_M-3.05GiB.gguf` | 3.05 GiB | image model (DiT), Q4_K (uniform sd.cpp K-quant recipe; the file name carries the standard label Q4_K_M so the Hub recognises it), with importance matrix | tested | tested | 22.7 / 14.2 dB |
| `Sakura-TextEncoder-Qwen3VL-4B-Instruct-8bit-3.99GiB.gguf` | 3.99 GiB | official Qwen3-VL-4B-Instruct text encoder, **unmodified**, GGUF Q8_0 (made with llama.cpp) | tested | - | - |
| `Qwen3-VL-4B-Instruct-bf16-8.27GiB.safetensors` | 8.27 GiB | official Qwen3-VL-4B-Instruct text encoder, **unmodified**, BF16, the two official shards merged into one file for the ComfyUI `CLIPLoader` | - | tested | - |
| `flux2-vae.safetensors` | 0.31 GiB | FLUX.2 VAE, unmodified copy of `ae.safetensors` of the official repository | tested | tested | - |
| `Sakura-FLUX.3-Image-Klein_ComfyUI_workflow_api_safetensors.json` | small | the same workflow with the standard UNET Loader for the official FLUX.3 Klein safetensors image model instead of a GGUF file (pick the file yourself) | - | not tested with the safetensors image model | - |
| `Sakura-FLUX.3-Image-Klein_ComfyUI_workflow_api.json` | small | ComfyUI workflow (API format), the same graph our test runs submitted | - | tested | - |

The columns say what we actually ran with that file: 🟦 stable-diffusion.cpp = one 1024x1024 image generated with it; 🟧 ComfyUI = the six test images below. "not tested" means we did not run it.

## Image-model quality (what we measured)

ComfyUI 0.41.1 with ComfyUI-GGUF, Radeon 8060S, 1024x1024, 16 steps, `euler`/`simple`, CFG 1.0, the official text encoder, seeds 42, 43, 44, 45, 46, 47, six neutral prompts, the BF16 original as reference. PSNR is against the BF16 image of the same prompt and seed; a diffusion model changes details even with tiny weight changes, so these are *deviation* numbers (higher = closer to BF16), not a quality score, and six prompts are not a benchmark. Mean over the six prompts and the lowest single value are in the table above.

**Time per image** (1024x1024, 16 steps, Radeon 8060S, nothing else running on the GPU, Q8_0 image model, official text encoder): ComfyUI 40.2 s once the models are loaded (50.2 s for the first image including loading); stable-diffusion.cpp 91.4 s per image as a one-shot `sd-cli` run including model loading. For comparison the BF16 image model took 36.2 s per image in ComfyUI: the GGUF files are smaller but **not faster** here, we did not investigate why.

Test prompts (the six prompts of the numbers above; seeds 42, 43, 44, 45, 46, 47) and their images with the Q8_0 file:

1. A close-up photograph of a red fox standing in fresh snow at sunrise, soft golden light, blurred pine forest in the background.
2. A still life photograph of a ceramic teapot, two lemons and a linen cloth on a wooden table, soft window light.
3. A wide landscape photograph of a mountain lake at dawn with mist over the water and pine trees on the shore.
4. A storefront with a bold white sign that reads SAKURA BAKERY on a dark green wall and a window showing loaves of bread.
5. A watercolor illustration of a lighthouse on a rocky coast under a stormy sky.
6. A macro photograph of a dew-covered spider web in morning light, shallow depth of field.

| ![fox](https://huggingface.co/webmp3/Sakura-FLUX.3-Image-Klein-GGUF/blob/02c8b1edfc3159a39e7443a9c94e283b7d1b7f3e/images/test_fox.png) | ![teapot](https://huggingface.co/webmp3/Sakura-FLUX.3-Image-Klein-GGUF/blob/02c8b1edfc3159a39e7443a9c94e283b7d1b7f3e/images/test_teapot.png) | ![lake](https://huggingface.co/webmp3/Sakura-FLUX.3-Image-Klein-GGUF/blob/02c8b1edfc3159a39e7443a9c94e283b7d1b7f3e/images/test_lake.png) |
|---|---|---|
| ![bakery](https://huggingface.co/webmp3/Sakura-FLUX.3-Image-Klein-GGUF/blob/02c8b1edfc3159a39e7443a9c94e283b7d1b7f3e/images/test_bakery.png) | ![lighthouse](https://huggingface.co/webmp3/Sakura-FLUX.3-Image-Klein-GGUF/blob/02c8b1edfc3159a39e7443a9c94e283b7d1b7f3e/images/test_lighthouse.png) | ![spiderweb](https://huggingface.co/webmp3/Sakura-FLUX.3-Image-Klein-GGUF/blob/02c8b1edfc3159a39e7443a9c94e283b7d1b7f3e/images/test_spiderweb.png) |

## What we changed

- `Sakura-FLUX.3-Image-Klein-*.gguf`: made with `sd-cli -M convert` (stable-diffusion.cpp commit `8cd731e`) from the root `model.safetensors` of `black-forest-labs/flux-3-image-klein` (revision `8454017f`), quantized to Q8_0 / Q6_K / Q5_K / Q4_K; one metadata key (`general.architecture = flux`) was added for ComfyUI-GGUF and the tensors were checked byte for byte against the converted file. The K-quant files marked "with importance matrix" were quantized with an importance matrix that we collected with stable-diffusion.cpp on the Q8_0 file (6 neutral text-to-image prompts, 448x448, 16 steps, 240 weight matrices). stable-diffusion.cpp `8cd731e` did not apply a loaded importance matrix to this model in convert mode (the lookup name lacked the `model.diffusion_model.` prefix), so these files were made with a local build with that one lookup fixed (not an upstream release). The blocks used only for reference-image conditioning (`content_mode_blocks.image_cond`) are not exercised by text-to-image prompts and were quantized without importance weights. We ship the importance-matrix file of a quant only where its mean PSNR against BF16 was not lower than the plain file's on our six images (decided per quant; with six prompts this is a weak criterion). Modified files.
- `Sakura-TextEncoder-Qwen3VL-4B-Instruct-8bit-*.gguf` and `Qwen3-VL-4B-Instruct-bf16-*.safetensors`: the official weights, unmodified (the `text_encoder/` of the FLUX.3 repository is byte-identical, SHA256 of both shards, to `Qwen/Qwen3-VL-4B-Instruct`); the GGUF was made with `convert_hf_to_gguf.py` (llama.cpp commit `9c2e0e491`) and `llama-quantize` (b11594), the safetensors file is the two official shards merged into one file.
- `flux2-vae.safetensors` is an unmodified copy of `ae.safetensors` of the official repository.

**Not measured:** image editing with reference images, the base (non-distilled) model, multi-reference prompts, other languages, speed on other hardware.

## License and use

Mixed, as described above: **FLUX Kommunity License** (`LICENSE.md`) for the image model files, the VAE and the workflow; **Apache-2.0** (`LICENSE-Apache-2.0.txt`) for the text-encoder files. Any rights to use the FLUX model and derivatives are granted directly by Black Forest Labs Inc. to the recipient under that license. See `NOTICE`.
Part of the **[Sakura Media](https://huggingface.co/collections/webmp3/sakura-media-6acdbccf37881e7c4187470c)** line.

## Credits

- Image model: [black-forest-labs/flux-3-image-klein](https://huggingface.co/black-forest-labs/flux-3-image-klein) (Black Forest Labs).
- Text encoder: [Qwen/Qwen3-VL-4B-Instruct](https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct) (Qwen team, Alibaba).
- Conversion and quantization: [leejet/stable-diffusion.cpp](https://github.com/leejet/stable-diffusion.cpp) (MIT), [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp) (MIT); loading: [city96/ComfyUI-GGUF](https://github.com/city96/ComfyUI-GGUF).

---

<details><summary>中文说明 · 樱花 (Simplified Chinese)</summary>

> English above。完整的独立中文版见 [README_zh.md](https://huggingface.co/webmp3/Sakura-FLUX.3-Image-Klein-GGUF/blob/02c8b1edfc3159a39e7443a9c94e283b7d1b7f3e/README_zh.md)。

**Built with FLUX.** [FLUX.3 Image Klein](https://huggingface.co/black-forest-labs/flux-3-image-klein)(蒸馏版,16 步,无 CFG)的社区量化版本,搭配官方 **未改动** 的 Qwen3-VL-4B-Instruct 文本编码器。属于独立工作,并非 Black Forest Labs 制作、审核或认可。

**两种许可证:** 图像模型文件、VAE 和工作流使用 FLUX Kommunity License(`LICENSE.md`:非商业用途;或仅在年收入低于 500 万美元的“合格用户”并按许可证要求进行过滤或审查时,商业使用生成的输出);文本编码器文件是未改动的 Qwen3-VL-4B-Instruct,使用 Apache-2.0(`LICENSE-Apache-2.0.txt`)。详见 `NOTICE`。

文本编码器的去审查版本(仅编码器,图像模型未改动)另有独立仓库:[Sakura-FLUX.3-Image-Klein-TextEncoder-Uncensored-GGUF](https://huggingface.co/webmp3/Sakura-FLUX.3-Image-Klein-TextEncoder-Uncensored-GGUF),可与本仓库的图像模型文件配合使用。

## 运行所需文件

| 部分 | 🟦 **stable-diffusion.cpp** | 🟧 **ComfyUI** |
|---|---|---|
| 图像模型 | `Sakura-FLUX.3-Image-Klein-Q8_0-5.58GiB.gguf`(最佳)或下表中更小的 K 量化文件,通过 `--diffusion-model` 传入 | 同一文件,用 **UNET Loader (GGUF)**([ComfyUI-GGUF](https://github.com/city96/ComfyUI-GGUF))加载 |
| 文本编码器 | `Sakura-TextEncoder-Qwen3VL-4B-Instruct-8bit-3.99GiB.gguf`,通过 `--llm` 传入 | `Qwen3-VL-4B-Instruct-bf16-8.27GiB.safetensors`,用常规 **Load CLIP** 节点加载,类型 `flux3` |
| VAE | `flux2-vae.safetensors`,通过 `--vae` 传入 | 同一文件,用 **Load VAE** 加载 |
| 程序 | [stable-diffusion.cpp](https://github.com/leejet/stable-diffusion.cpp/releases) `master-968-8cd731e` 或更新版本的 `sd-cli`(我们使用 commit `8cd731e`,Vulkan 构建),不包含 | ComfyUI 0.41.0 或更新版本(我们使用 0.41.1)及 ComfyUI-GGUF 自定义节点,不包含 |

```bash
sd-cli --diffusion-model Sakura-FLUX.3-Image-Klein-Q8_0-5.58GiB.gguf --llm Sakura-TextEncoder-Qwen3VL-4B-Instruct-8bit-3.99GiB.gguf --vae flux2-vae.safetensors -p "your prompt" --cfg-scale 1.0 --steps 16 --sampling-method euler -W 1024 -H 1024 -o out.png
```

ComfyUI:把 `Sakura-FLUX.3-Image-Klein_ComfyUI_workflow_api.json` 拖入 ComfyUI 即可(采样器 `euler`,调度器 `simple`,16 步,CFG 1.0,1024x1024,种子 42,即我们测试过的设置)。

## 我们的测量

- **图像模型相对 BF16 的偏离**(ComfyUI 0.41.1,Radeon 8060S,1024x1024,16 步,6 条中性提示,种子 42, 43, 44, 45, 46, 47,官方文本编码器):见英文版文件表中的 PSNR 列(均值 / 最小值)。扩散模型即使权重变化很小也会改变细节,所以这是偏离度,不是质量评分,6 条提示也不是基准测试。
- **每张图耗时:** 见英文版(只有在 GPU 空闲时的测量才会写入)。GGUF 文件更小,但在这里并不更快(需要即时反量化)。
- **没有测量:** 参考图像编辑、基础(非蒸馏)模型、多参考提示、其他语言、其他硬件上的速度。

## 许可与致谢

FLUX Kommunity License(图像模型文件、VAE、工作流)与 Apache-2.0(文本编码器文件);详见 `NOTICE`。属于 **[Sakura Media](https://huggingface.co/collections/webmp3/sakura-media-6acdbccf37881e7c4187470c)** 系列。致谢:Black Forest Labs(FLUX.3 Image Klein)、Qwen / Alibaba(Qwen3-VL-4B-Instruct)、leejet/stable-diffusion.cpp、ggml-org/llama.cpp、city96/ComfyUI-GGUF。

</details>
