# Self-hosted fonts — AMD ComfyUI Guide

Subset `woff2` files for the landing page. No font CDN, no runtime
downloads: `index.html` references these files with `@font-face`
(relative `assets/fonts/...` URLs) and `font-display: swap`.

**Direction:** *Darkroom Archive* — editorial serif display (Latin
*Instrument Serif*, CJK *Noto Serif SC*), refined body sans (Latin
*IBM Plex Sans*, CJK *Noto Sans SC*), and *IBM Plex Mono* for metadata,
eyebrows and plate numbers.

**Total:** 11 files, 348816 bytes (340.6 KB).

## Inventory

| File | Family | Weight | Style | Glyphs | Bytes |
|---|---|---:|---|---:|---:|
| `instrument-serif-400.woff2` | Instrument Serif | 400 | normal | 193 | 20508 (20.0 KB) |
| `instrument-serif-400-italic.woff2` | Instrument Serif | 400 | italic | 193 | 21232 (20.7 KB) |
| `ibm-plex-sans-400.woff2` | IBM Plex Sans | 400 | normal | 220 | 21252 (20.8 KB) |
| `ibm-plex-sans-500.woff2` | IBM Plex Sans | 500 | normal | 220 | 23220 (22.7 KB) |
| `ibm-plex-mono-400.woff2` | IBM Plex Mono | 400 | normal | 219 | 14544 (14.2 KB) |
| `ibm-plex-mono-500.woff2` | IBM Plex Mono | 500 | normal | 219 | 14984 (14.6 KB) |
| `noto-serif-sc-500.woff2` | Noto Serif SC | 500 | normal | 329 | 55768 (54.5 KB) |
| `noto-serif-sc-600.woff2` | Noto Serif SC | 600 | normal | 329 | 56040 (54.7 KB) |
| `noto-sans-sc-400.woff2` | Noto Sans SC | 400 | normal | 428 | 58632 (57.3 KB) |
| `noto-sans-sc-500.woff2` | Noto Sans SC | 500 | normal | 428 | 59112 (57.7 KB) |
| `ui-symbols-400.woff2` | UI Symbols | 400 | normal | 22 | 3524 (3.4 KB) |

## Provenance

All families are licensed under the SIL Open Font License 1.1. Sources
are the Google Fonts mirror (`github.com/google/fonts`); license texts
are committed next to the fonts as `OFL-*.txt`.

| Family | Upstream file | Source URL |
|---|---|---|
| Instrument Serif | `instrumentserif/InstrumentSerif-Regular.ttf` | <https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/instrumentserif/InstrumentSerif-Regular.ttf> |
| Instrument Serif | `instrumentserif/InstrumentSerif-Italic.ttf` | <https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/instrumentserif/InstrumentSerif-Italic.ttf> |
| IBM Plex Sans | `ibmplexsans/IBMPlexSans[wdth,wght].ttf` | <https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/ibmplexsans/IBMPlexSans%5Bwdth,wght%5D.ttf> |
| IBM Plex Mono | `ibmplexmono/IBMPlexMono-Regular.ttf` | <https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/ibmplexmono/IBMPlexMono-Regular.ttf> |
| IBM Plex Mono | `ibmplexmono/IBMPlexMono-Medium.ttf` | <https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/ibmplexmono/IBMPlexMono-Medium.ttf> |
| Noto Serif SC | `notoserifsc/NotoSerifSC[wght].ttf` | <https://raw.githubusercontent.com/google/fonts/main/ofl/notoserifsc/NotoSerifSC%5Bwght%5D.ttf> |
| Noto Sans SC | `notosanssc/NotoSansSC[wght].ttf` | <https://raw.githubusercontent.com/google/fonts/main/ofl/notosanssc/NotoSansSC%5Bwght%5D.ttf> |
| UI Symbols | `notosanssymbols2/NotoSansSymbols2-Regular.ttf` | <https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/notosanssymbols2/NotoSansSymbols2-Regular.ttf> |

## Font stacks

```css
:root {
  --font-display: "Instrument Serif", "Noto Serif SC", "UI Symbols", "Songti SC", Georgia, serif;
  --font-body: "IBM Plex Sans", "Noto Sans SC", "UI Symbols", "PingFang SC", "Microsoft YaHei", system-ui, sans-serif;
  --font-mono: "IBM Plex Mono", "UI Symbols", ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}
```

`UI Symbols` only carries the handful of control glyphs the text
families lack (`▶` play, `❚` pause, `✕` close); it is 1-2 KB and must
come *after* the text faces in each stack.

Latin faces come first so mixed Chinese/Latin text gets Latin serif/
sans glyphs; CJK faces carry only CJK-range glyphs and fill the rest.
Attribute-level typography (sizes, tracking, motion) is specified in
`runs/design/typography-spec.md`.

## Rebuild

```bash
# 1. fetch OFL sources (cached in runs/font-src/, gitignored; ~45 MB)
python3 scripts/build_fonts.py --download
# 2. subset + emit woff2 (needs fontTools + brotli from runs/fonttools)
PYTHONPATH=runs/fonttools python3 scripts/build_fonts.py
# 3. verify page/gallery glyph coverage (fontTools)
PYTHONPATH=runs/fonttools python3 scripts/build_fonts.py --coverage
# 4. stdlib-only integrity check (CI safe, no third-party imports)
python3 scripts/build_fonts.py --check
```

The builder extracts its glyph set from
`runs/redesign-2026-10-31/copy.md`, `index.html` and (when present)
`assets/gallery/manifest.json`. Re-run step 2 + 3 whenever page copy
or gallery prompts change so no glyph silently falls back to a system
font.

## Subset policy

- Latin subset: ASCII printable, Latin-1 supplement, editorial dashes /
  quotes / bullets, and the arrows used by CTAs (`↗`) and back-to-top
  (`↑`), plus any Latin character found in the page text.
- CJK serif subset: CJK characters from `copy.md` + `index.html` (all
  display text) plus CJK punctuation and common symbols.
- CJK sans subset: the serif set **plus** every character in the gallery
  manifest (model labels and real prompts shown in the lightbox).
- OpenType layout (`GSUB`/`GPOS`, all features) is preserved so kerning
  and punctuation shaping stay correct.

## Build metadata

Deterministic output (fixed `head` timestamps, minimal name table,
sorted Unicode sets), so repeated builds produce identical bytes.

| File | Bytes | SHA-256 | Upstream source SHA-256 |
|---|---:|---|---|
| `instrument-serif-400.woff2` | 20508 | `d6fcb9a4df011b8e…` | `498efd461f6ddfcb…` |
| `instrument-serif-400-italic.woff2` | 21232 | `bc831fbf31271e62…` | `08939b8bdf534afe…` |
| `ibm-plex-sans-400.woff2` | 21252 | `3e817545f681e0a8…` | `3b031aa421617420…` |
| `ibm-plex-sans-500.woff2` | 23220 | `681dc07598a60ecc…` | `3b031aa421617420…` |
| `ibm-plex-mono-400.woff2` | 14544 | `96d7bcd6c50c7e14…` | `6a3412f058c7d8df…` |
| `ibm-plex-mono-500.woff2` | 14984 | `c60e5b65c5b86085…` | `a9b4c49bb299e05b…` |
| `noto-serif-sc-500.woff2` | 55768 | `2ab115da436bdd65…` | `050080d9255a8680…` |
| `noto-serif-sc-600.woff2` | 56040 | `64e48e6ae973ca48…` | `050080d9255a8680…` |
| `noto-sans-sc-400.woff2` | 58632 | `0e67c035a5ab6bbc…` | `a3041811a78c361b…` |
| `noto-sans-sc-500.woff2` | 59112 | `25ace1cb2f64b36b…` | `a3041811a78c361b…` |
| `ui-symbols-400.woff2` | 3524 | `63a70737a671c308…` | `7d5fb73b7ca67a67…` |
