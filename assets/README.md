# Visual assets

README visual assets, built from real model outputs captured on the RX 6650 XT.

| File | Purpose |
|---|---|
| `banner.webp` | README cover: project name, tagline, verified-hardware line |
| `features.webp` | Core outputs: four model families, one real image each, plus result counts |

## Sources

All images are untouched official test outputs (512×512) from public evidence in this repository. Copies are kept in `assets/src/` so the posters can be rebuilt without touching the evidence tree.

| `assets/src/` | Original path | Model / feature |
|---|---|---|
| `qwen21-turbo-cat.png` | `ComfyUI/output/Liuyue_Qwen21_Turbo_RX6650XT_00001_.png` | Qwen Image 2.1 Turbo, text to image |
| `flux2-klein-watercolor-cat.png` | `ComfyUI/output/FeatureBench/flux2-klein-style_00001_.png` | FLUX.2 Klein, style edit |
| `kroma-q2-forest-fox.png` | `ComfyUI/output/Liuyue_Kroma031_Q2_4step_RX6650XT_00001_.png` | Kroma Q2, 4-step sampling |
| `moss-sft-astronaut.png` | `evidence/2026-10-21-repairs/cases/moss-watercolor-base-sft/10-0-moss-watercolor-base-sft_00001_.png` | MOSS SFT, 8-step LoRA |
| `qwen-multiref-fox.png` | `ComfyUI/output/FeatureBench/qwen-multiref_00001_.png` | Qwen Image 2.1, multi-reference (banner background) |

## Rebuild

The posters are plain HTML/CSS rendered at 1920×1080 with headless Chrome, then converted to WebP.

```bash
google-chrome --headless=new --disable-gpu --hide-scrollbars \
  --window-size=1920,1080 --virtual-time-budget=6000 \
  --screenshot="$PWD/assets/banner.png" "file://$PWD/scripts/readme_assets/banner.html"
google-chrome --headless=new --disable-gpu --hide-scrollbars \
  --window-size=1920,1080 --virtual-time-budget=6000 \
  --screenshot="$PWD/assets/features.png" "file://$PWD/scripts/readme_assets/features.html"
magick assets/banner.png -strip -quality 86 assets/banner.webp
magick assets/features.png -strip -quality 86 assets/features.webp
rm assets/banner.png assets/features.png
```

The poster sources live in `scripts/readme_assets/`; edit those, not the WebP files.
