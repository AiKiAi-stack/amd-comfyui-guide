# Visual assets

README visual assets and the landing-page model gallery, built from real model outputs captured on the RX 6650 XT.

| File | Purpose |
|---|---|
| `banner.webp` | README cover: project name, tagline, verified-hardware line |
| `features.webp` | Core outputs poster: four model families, one real image each — no result counts, no pass/fail verdicts |
| `gallery/manifest.json` | Landing-page gallery manifest: 7 model families, 32 curated real outputs with prompts, parameters and evidence anchors |
| `gallery/*.webp` | 32 curated model outputs, one file per source PNG |

## Landing-page gallery

`assets/gallery/` is the image set the guide's gallery section loads. Curation is explicit in the `CURATION` constant in `scripts/build_gallery.py`: real outputs only — no inputs, masks, control images, noise experiments, or the incomplete `zimage-aio-figure-art`.

| Property | Rule |
|---|---|
| File name | `assets/gallery/<slug>.webp`; slug = source PNG basename without the `_00001_` suffix, lower-kebab |
| Pixels | native source size, never upscaled (most `512×512`; three FLUX.2 portraits at `368×672` / `368×688`; one Qwen Base at `768×768`) |
| Encoding | Pillow `quality=82, method=6` |
| Metadata | none — no EXIF/XMP/ICC (`scripts/verify_publication.py` rejects image metadata) |
| Manifest | `{schema, generated, models[7], plates[32]}`; each plate has `id, model_id, feature_id, feature, prompt, width, height, image, source, report, steps, sampler, hero` |
| Heroes | exactly one `hero: true` plate per model family, used by the page's projector |

The manifest carries no pass/fail verdict data: per-feature verdicts stay inside `report/index.html`; guide surfaces do not present them.

Sources are the recorded outputs from `evidence/2026-10-19-features/platform-comparison.json`. Each plate's `source` field keeps the historical runtime capture path (`ComfyUI/output/...`) for provenance; the committed copies of those image files live under `evidence/report-assets/output/...`. `--build` resolves either tree (historical path first, archive second), and `--check` validates the exported WebP files only — a missing historical PNG location does not fail the check.

```bash
python3 scripts/build_gallery.py --build   # local only: needs Pillow; exports the WebPs and rewrites the manifest
python3 scripts/build_gallery.py --check   # stdlib only, CI safe: manifest, files, dimensions, report anchors, no verdict data
```

## Poster sources

All poster images are untouched official test outputs (512×512) from public evidence in this repository. Copies are kept in `assets/src/` so the posters can be rebuilt without touching the evidence tree.

| `assets/src/` | Original path | Model / feature |
|---|---|---|
| `qwen21-turbo-cat.png` | `evidence/report-assets/output/Liuyue_Qwen21_Turbo_RX6650XT_00001_.png` | Qwen Image 2.1 Turbo, text to image |
| `flux2-klein-watercolor-cat.png` | `evidence/report-assets/output/FeatureBench/flux2-klein-style_00001_.png` | FLUX.2 Klein, style edit |
| `kroma-q2-forest-fox.png` | `evidence/report-assets/output/Liuyue_Kroma031_Q2_4step_RX6650XT_00001_.png` | Kroma Q2, 4-step sampling |
| `moss-sft-astronaut.png` | `evidence/2026-10-21-repairs/cases/moss-watercolor-base-sft/10-0-moss-watercolor-base-sft_00001_.png` | MOSS SFT, 8-step LoRA |
| `qwen-multiref-fox.png` | `evidence/report-assets/output/FeatureBench/qwen-multiref_00001_.png` | Qwen Image 2.1, multi-reference (banner background) |

## Rebuild

The posters are plain HTML/CSS rendered at 1920×1080 with headless Chrome, then converted to WebP. The poster sources live in `scripts/readme_assets/`; edit those, not the WebP files.

`features.webp` has no footer strip: its bottom stats/verdict line was removed, so the four images carry the composition. Rebuild it with Pillow (no metadata):

```bash
google-chrome --headless=new --no-sandbox --disable-gpu --hide-scrollbars \
  --window-size=1920,1080 --virtual-time-budget=6000 \
  --screenshot="$PWD/assets/features.png" "file://$PWD/scripts/readme_assets/features.html"
python3 - <<'PY'
from PIL import Image
Image.open("assets/features.png").convert("RGB").save(
    "assets/features.webp", "WEBP", quality=86, method=6
)
PY
rm assets/features.png   # keep the repo free of intermediate PNGs/metadata
```

`banner.webp` is unchanged and still rebuilt from `banner.html` with ImageMagick:

```bash
google-chrome --headless=new --disable-gpu --hide-scrollbars \
  --window-size=1920,1080 --virtual-time-budget=6000 \
  --screenshot="$PWD/assets/banner.png" "file://$PWD/scripts/readme_assets/banner.html"
magick assets/banner.png -strip -quality 86 assets/banner.webp
rm assets/banner.png
```
