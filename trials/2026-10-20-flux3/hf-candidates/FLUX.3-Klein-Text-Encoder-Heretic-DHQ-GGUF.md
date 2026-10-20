---
license: apache-2.0
base_model:
- Qwen/Qwen3-VL-4B-Instruct
tags:
- gguf
- quantized
- text-encoder
- abliterated
- heretic
- flux
- flux-3
---

# FLUX.3 Klein Text Encoder (Heretic Qwen3-VL-4B) — DHQ GGUF

FLUX.3 Klein's text encoder is Qwen3-VL-4B-Instruct, unmodified. This repo has a **heretic (abliterated)** version of
it, in bf16 and as a GGUF quantized with **DHQ = Dual-Head Quant**: every tensor gets the precision that matters to
**what the FLUX.3 Klein DiT actually reads**, measured per tensor with gradients through the DiT's own text path, and
checked a second time for prompt writing.

**Made mainly for Dual-Head Dragon** (one model as both the prompt enhancer and the text encoder), but it works as a
plain FLUX.3 Klein text encoder too: the bf16 file with ComfyUI's own `CLIPLoader`, the GGUF with ComfyUI-GGUF or
llama.cpp (see *How to load*).

| File | What | Size |
|---|---|---:|
| `flux3-klein-te-heretic-bf16.safetensors` | heretic text encoder, bf16, ComfyUI single file (vision tower included) | 8.88 GB |
| `flux3-klein-te-heretic-dhq-Q4_K_M.gguf` | the same, DHQ GGUF | 2.66 GB |
| `mmproj-flux3-klein-te-heretic-dhq-f16.gguf` | vision tower for the GGUF | 0.84 GB |

- **Heretic**: refusals 2/100 (original 97/100), KL divergence 0.037 to the original
  ([Heretic](https://github.com/p-e-w/heretic), 892-trial search). Only `self_attn.o_proj` in 31 layers is changed;
  everything else is bit-identical to Qwen3-VL-4B-Instruct.
- **One file, `Q4_K_M` class, 2.66 GB**: the `Q4_K_M` budget plus 165 MB spent on the tensors FLUX.3's padding depends
  on (see below). Fewer errors than the standard `Q4_K_M` on every measure.

## About the DHQ series

DHQ files are quantized **for use as a diffusion model's text encoder**: each tensor's precision is chosen by how
much its quantization error changes what the target DiT reads (measured through the DiT's own text-input stage),
not by next-token loss. They stay normal LLM GGUFs, so the same file can still write or rewrite prompts: where a
model is also used as a prompt enhancer, every file is also checked for that (the PE column) and the tables show where
it gets worse.

DHQ repos: [Qwen-Image-2.1](https://huggingface.co/pottokao/Qwen-Image-2.1-Text-Encoder-Heretic-DHQ-GGUF) ·
[Ideogram 4](https://huggingface.co/pottokao/Ideogram-4-Text-Encoder-Heretic-DHQ-GGUF) ·
[Boogu](https://huggingface.co/pottokao/Boogu-Text-Encoder-Heretic-DHQ-GGUF) ·
[Z-Image-Engineer-V6](https://huggingface.co/pottokao/Z-Image-Engineer-V6-DHQ-GGUF) ·
[Qwen3-4B (Z-Image / FLUX.2 klein 4B)](https://huggingface.co/pottokao/Qwen3-4B-Text-Encoder-DHQ-GGUF) ·
[FLUX.3 Klein](https://huggingface.co/pottokao/FLUX.3-Klein-Text-Encoder-Heretic-DHQ-GGUF)

We also built **Dual-Head Dragon** ([ComfyUI-DualHead-Dragon](https://github.com/pottokao-dotcom/ComfyUI-DualHead-Dragon)), a ComfyUI node that runs one GGUF as both the text encoder and the prompt
enhancer (llama.cpp inside). It is public but **still in testing**. For FLUX.3 Klein it is used for **prompt rewriting only** (see *Master styles on
FLUX.3 Klein*); encode with ComfyUI's own loader. The files here work without it (see *How to load*).

## Results

Same heretic bf16 source. **Standard** = llama.cpp `Q4_K_M` rules + the same imatrix.
**TE** = relative error of the text conditioning after FLUX.3 Klein's text path (`txt_in` and the 5 text-only blocks,
which run once per prompt, before the image is involved), on 36 held-out prompts never used to build or pick anything,
split into the prompt's own tokens and the padding (lower is better). **PE** = mean KL divergence of next-token
predictions vs bf16 on 80 prompt-rewrite samples written with BFL's own t2i system prompt (lower is better).

| File | Size | TE text | TE padding | PE |
|---|---:|---:|---:|---:|
| standard `Q4_K_M` (not uploaded) | 2.50 GB | 2.77% | 11.4% | 0.0319 |
| DHQ at the exact `Q4_K_M` size (not uploaded) | 2.50 GB | 2.33% | 8.2% | 0.0246 |
| **`flux3-klein-te-heretic-dhq-Q4_K_M.gguf`** | **2.66 GB** | **2.15%** | **6.5%** | **0.0235** |

**Why the padding matters.** FLUX.3 Klein pads every prompt to a multiple of 80 tokens, and the DiT attends to the
padding: a 20-word prompt is three quarters padding. The padding has no content of its own, its hidden states come
almost entirely from attention to the real tokens, so quantization errors in attention hit it hard: at plain 4 bit its
error per position is ~50× that of the text, and one tensor (layer 0 `q_proj`) carries a third of it. The uploaded
file puts the 32 tensors that matter most to the padding at Q8_0 (+165 MB), which takes the padding error from 11.4%
to 6.5%. Raising `token_embd` (also the output layer here) to Q8_0 as well was tested and changed nothing.

How TE was measured: each GGUF's quantized weights were dequantized exactly into ComfyUI's own FLUX.3 text encoder
(templates, padding and the 8 tapped layers as in ComfyUI), then scored through the DiT's text path. This covers the
whole weight error but not the activation rounding llama.cpp adds at run time (small at 4–5 bit).

**The heretic model itself**, vs the original on the same benchmark subsets (bf16, chat template): GSM8K 85% vs 87%
(100 problems), IFEval 82% vs 80% (50 prompts) — within sampling noise.

**As a prompt enhancer.** BFL's model card says FLUX.3 Klein should not be used without a prompt upsampler. This model
can rewrite prompts with BFL's [`system_prompts.json`](https://huggingface.co/black-forest-labs/flux-3-image-klein-pup),
and it does not refuse. In a small side-by-side (4 prompts, same seed), BFL's own upsampler (a fine-tuned Qwen3.5-9B)
followed stated styles and framing better (e.g. it keeps "charcoal drawing" a drawing); the untuned Qwen3.5-9B made the
same mistakes as this 4B, so the gap comes from BFL's fine-tune, not the model size. Note: ComfyUI's `TextGenerate`
node does not work with the `flux3` text encoder type (it returns `#`, also with the original bf16 weights); rewrite
with llama.cpp instead.

## How to load

**ComfyUI, bf16**: put `flux3-klein-te-heretic-bf16.safetensors` in `models/text_encoders/` and load it with the
standard `CLIPLoader`, **type `flux3`**, in place of `qwen3vl_4b_bf16.safetensors` in BFL's FLUX.3 Klein workflow. No
add-on needed. The tensor names are the Hugging Face ones: renamed to `model.safetensors` next to the source repo's
config and tokenizer files, it also loads with `transformers`.

**ComfyUI, GGUF**: needs [ComfyUI-GGUF](https://github.com/city96/ComfyUI-GGUF) **and** the add-on
[ComfyUI-GGUF-Qwen3VL-TE](https://github.com/pottokao-dotcom/ComfyUI-GGUF-Qwen3VL-TE) (commit `3eea253` or later), and a
ComfyUI with FLUX.3 support. Put the GGUF **and** `mmproj-flux3-klein-te-heretic-dhq-f16.gguf` (this repo) in
`models/text_encoders/` without renaming them (the mmproj is found by file-name prefix), then `CLIPLoaderGGUF` with
**type `flux3`**, in place of the text encoder loader of BFL's FLUX.3 Klein workflow.

> [!WARNING]
> Without the add-on (or with an older version) ComfyUI does not see the vision tower and builds the **Z-Image**
> (Qwen3-4B) text encoder from this file, **without an error**: one 2560-wide layer instead of FLUX.3's 8 stacked layers.
> With the add-on the conditioning matches the bf16 safetensors encoder (per-token cos 1.0000 on text, 0.9999 on
> padding, checked with a Q8_0 GGUF on ComfyUI 0.41.0).

**llama.cpp / Dual-Head Dragon**: a standard `qwen3vl` GGUF (text generation, prompt rewriting). The mmproj adds
image input.

## Master styles on FLUX.3 Klein

The [Master Style](https://github.com/pottokao-dotcom/master_dh_sp) prompt enhancer (role-play system prompt + style
cards) runs on this GGUF in [Dual-Head Dragon](https://github.com/pottokao-dotcom/ComfyUI-DualHead-Dragon) with its
4B LoRA and DFlash2 draft, and FLUX.3 Klein draws the result. Nothing new to install beyond those two nodes:

| Step | Node | Setting |
|---|---|---|
| system prompt | `Master Style Prompt` | style card, **engine `zimage`** |
| + Klein section | `StringConcatenate` (core) | `string_b` = [`klein/master-style-klein-section.txt`](https://huggingface.co/pottokao/FLUX.3-Klein-Text-Encoder-Heretic-DHQ-GGUF/blob/2d87f23da080416e74b05db8c772186eb2b29e2c/klein/master-style-klein-section.txt) |
| rewrite | `DualHeadDragonLoader` + `DualHeadRewrite` | `flux3-klein-te-heretic-dhq-Q4_K_M.gguf`, **type `lumina2`** (rewrite only), LoRA [`…-ck1212-qwen3vl-f16.gguf`](https://huggingface.co/pottokao/zeng-v6_master-pe_lora_v4.1-r32-ep2_20260928), draft [`…-dflash2_v4.1-b16-gen5_20260930-vocab16k-Q4_K_M.gguf`](https://huggingface.co/pottokao/Z-Image-Engineer-V6-DFlash2-b16) |
| finish | `Master Style Finalize` | same card; gives width / height |
| encode | `CLIPLoader` (core) | `flux3-klein-te-heretic-bf16.safetensors` (or the original), **type `flux3`** |
| draw | FLUX.3 Klein | BFL's template: 15 steps, `er_sde` / `simple`, cfg 1 |

The whole graph: [`klein/workflow-flux3-klein-master-style-api.json`](https://huggingface.co/pottokao/FLUX.3-Klein-Text-Encoder-Heretic-DHQ-GGUF/blob/2d87f23da080416e74b05db8c772186eb2b29e2c/klein/workflow-flux3-klein-master-style-api.json)
(ComfyUI API format; Monet card, seed 42).

- **The system prompt** is the Master Style one for Z-Image, unchanged (the LoRA was trained on it), followed by a short
  section with FLUX.3 Klein's caption conventions from BFL's own upsampler prompt: open with the medium (a photograph
  as a photograph; a painting, print or poster by its own medium), one prose block, every person an adult with an
  observable profile, frame-relative positions, quoted text verbatim.
- **Type `lumina2`** only picks a Qwen3 chat template for rewriting; Dual-Head Dragon has no FLUX.3 encoder type yet, so
  the encoding is done by ComfyUI's `CLIPLoader`. The text encoder is then in memory twice (the 2.66 GB GGUF for
  rewriting + the 8.88 GB bf16 file for encoding); on a 16 GB card ComfyUI swaps models between steps.
- **Speed** (RTX 5060 Ti 16 GB): rewrite ~5 s (DFlash2, ~480 tokens), image ~13 s with the swapping above.
- **The LoRA was trained on Z-Image-Engineer V6 (Qwen3-4B), not on this model.** With this system prompt, 129 rewrites
  (15 painters, 11 poster styles, 12 photo styles, these samples) never ran away. Long system prompts of your own can
  make it repeat itself until `max_new_tokens`; run it again or shorten the prompt.

Samples: the 29 Master Style showcase prompts (same prompts and seeds as the
[Dual-Head Dragon showcase](https://github.com/pottokao-dotcom/ComfyUI-DualHead-Dragon) for the other image models),
FLUX.3 Klein NVFP4, settings as above.

<table>
<tr><td width="25%" valign="top"><img src="showcase/01.jpg" width="100%"><br><sub><b>#1</b> <code>pe-default</code><br>Dancers carrying a golden dragon on poles through the lantern-lit streets of Chinatown in San Francisco at Lunar New Year</sub></td><td width="25%" valign="top"><img src="showcase/02.jpg" width="100%"><br><sub><b>#2</b> <code>bw-geometric-street-candid</code><br>A ballerina leaping across the zebra crossing in Shibuya</sub></td><td width="25%" valign="top"><img src="showcase/03.jpg" width="100%"><br><sub><b>#3</b> <code>rainy-window-abstract-portrait</code><br>A girl in a yellow raincoat waiting under the neon signs of Mong Kok on a rainy night</sub></td><td width="25%" valign="top"><img src="showcase/04.jpg" width="100%"><br><sub><b>#4</b> <code>refined-minimalist-studio-portrait</code><br>A young maiko in kimono and full white makeup glancing over her shoulder</sub></td></tr>
<tr><td width="25%" valign="top"><img src="showcase/05.jpg" width="100%"><br><sub><b>#5</b> <code>saturated-banal-monumental</code><br>A giant inflatable rubber duck floating in Victoria Harbour, the Hong Kong skyline behind it</sub></td><td width="25%" valign="top"><img src="showcase/06.jpg" width="100%"><br><sub><b>#6</b> <code>bw-dramatic-chiaroscuro</code><br>A lone samurai standing in a bamboo forest as light pierces the mist</sub></td><td width="25%" valign="top"><img src="showcase/07.jpg" width="100%"><br><sub><b>#7</b> <code>surreal-staged-monochrome</code><br>A woman in a ball gown holding a white umbrella on the salt flats of Uyuni</sub></td><td width="25%" valign="top"><img src="showcase/08.jpg" width="100%"><br><sub><b>#8</b> <code>bw-ink-wash-landscape</code><br>Hot air balloons drifting over the misty temples of Bagan at sunrise</sub></td></tr>
<tr><td width="25%" valign="top"><img src="showcase/09.jpg" width="100%"><br><sub><b>#9</b> <code>vintage-bw-elegant-candid</code><br>A glamorous couple dancing in a 1930s Shanghai ballroom</sub></td><td width="25%" valign="top"><img src="showcase/10.jpg" width="100%"><br><sub><b>#10</b> <code>hyper-saturated-cinematic-unease</code><br>A beauty queen eating cake alone in a pink motel room in Palm Springs</sub></td><td width="25%" valign="top"><img src="showcase/11.jpg" width="100%"><br><sub><b>#11</b> <code>raw-bw-cinematic-portraits</code><br>A boxer catching his breath after a fight in a Bangkok gym</sub></td><td width="25%" valign="top"><img src="showcase/12.jpg" width="100%"><br><sub><b>#12</b> <code>high-gloss-noir-glamour</code><br>A femme fatale in a black velvet dress on a Hong Kong rooftop at night, the skyline behind her</sub></td></tr>
<tr><td width="25%" valign="top"><img src="showcase/13.jpg" width="100%"><br><sub><b>#13</b> <code>minimalist-color-landscapes</code><br>A single red umbrella on an empty turquoise beach in the Maldives</sub></td><td width="25%" valign="top"><img src="showcase/14.jpg" width="100%"><br><sub><b>#14</b> <code>soft-warm-nostalgic</code><br>Kids jumping into the sea from a harbour wall in Sicily on a summer afternoon</sub></td><td width="25%" valign="top"><img src="showcase/15.jpg" width="100%"><br><sub><b>#15</b> <code>monet_style</code><br>A garden party under hanging wisteria in full bloom in Kyoto</sub></td><td width="25%" valign="top"><img src="showcase/16.jpg" width="100%"><br><sub><b>#16</b> <code>hokusai_style</code><br>A giant wave crashing over the New York skyline</sub></td></tr>
<tr><td width="25%" valign="top"><img src="showcase/17.jpg" width="100%"><br><sub><b>#17</b> <code>swiss-international-style</code><br>A poster for a Tokyo techno festival</sub></td><td width="25%" valign="top"><img src="showcase/18.jpg" width="100%"><br><sub><b>#18</b> <code>art-deco-travel-poster</code><br>A travel poster of a zeppelin flying to Shanghai, titled &quot;Shanghai&quot;</sub></td><td width="25%" valign="top"><img src="showcase/19.jpg" width="100%"><br><sub><b>#19</b> <code>japanese-modernist-geometric</code><br>A poster for a koi festival in Kyoto</sub></td><td width="25%" valign="top"><img src="showcase/20.jpg" width="100%"><br><sub><b>#20</b> <code>pe-default</code><br>A beautiful young woman with a shaved head, thick eyebrows and a small silver nose ring, laughing on a scooter through the streets of Taipei at dusk</sub></td></tr>
<tr><td width="25%" valign="top"><img src="showcase/21.jpg" width="100%"><br><sub><b>#21</b> <code>raw-bw-cinematic-portraits</code><br>A beautiful woman in her fifties with freckles, a gap-toothed smile and wild grey curls, leaning out of a tram window in Lisbon</sub></td><td width="25%" valign="top"><img src="showcase/22.jpg" width="100%"><br><sub><b>#22</b> <code>soft-warm-nostalgic + swiss-international-style</code><br>A fashion poster titled &quot;PARIS&quot;, a fashionable woman on the terrace of a luxury Paris penthouse, the Eiffel Tower behind her</sub></td><td width="25%" valign="top"><img src="showcase/23.jpg" width="100%"><br><sub><b>#23</b> <code>refined-minimalist-studio-portrait + japanese-modernist-geometric</code><br>A colour beauty magazine cover titled &quot;BLOOM&quot;, a young Korean woman with dewy skin and peach blush</sub></td><td width="25%" valign="top"><img src="showcase/24.jpg" width="100%"><br><sub><b>#24</b> <code>van_gogh_style</code><br>Drunk salarymen in loosened ties stumbling home under a full moon in Shinjuku, Tokyo</sub></td></tr>
<tr><td width="25%" valign="top"><img src="showcase/25.jpg" width="100%"><br><sub><b>#25</b> <code>rainy-window-abstract-portrait</code><br>A young woman in a clear transparent raincoat over a bikini, laughing under the neon signs of Mong Kok on a rainy night</sub></td><td width="25%" valign="top"><img src="showcase/26.jpg" width="100%"><br><sub><b>#26</b> <code>high-gloss-noir-glamour + swiss-international-style</code><br>A fashion poster for Milan couture week titled &quot;MILANO&quot;, a model in a sculptural white coat</sub></td><td width="25%" valign="top"><img src="showcase/27.jpg" width="100%"><br><sub><b>#27</b> <code>hyper-saturated-cinematic-unease + japanese-modernist-geometric</code><br>A fashion poster for a Tokyo streetwear brand titled &quot;NEON&quot;, a girl in a candy-pink puffer jacket</sub></td><td width="25%" valign="top"><img src="showcase/28.jpg" width="100%"><br><sub><b>#28</b> <code>refined-minimalist-studio-portrait + swiss-international-style</code><br>A beauty magazine cover titled &quot;GLOW&quot;, a close-up of a woman with glossy red lips and slicked-back hair</sub></td></tr>
<tr><td width="25%" valign="top"><img src="showcase/29.jpg" width="100%"><br><sub><b>#29</b> <code>soft-warm-nostalgic + japanese-modernist-geometric</code><br>A beauty magazine cover titled &quot;BLOOM&quot;, a young Korean woman with dewy skin and peach blush</sub></td></tr>
</table>

## Reproducibility

`recipes/` has the full recipe: source repo and revision, the heretic parameters (to rebuild the heretic weights
from Qwen3-VL-4B-Instruct), the llama.cpp commit, the importance matrix with its calibration text, and the type of
every tensor (`*.grid.md` shows them per layer). Built on aarch64 (GB10).

## License

Apache-2.0, same as the base weights (Qwen3-VL-4B-Instruct, Alibaba Cloud / Qwen). See `LICENSE` and `NOTICE`. This
repo contains no FLUX.3 weights; FLUX.3 Klein is released by Black Forest Labs under its own license.
