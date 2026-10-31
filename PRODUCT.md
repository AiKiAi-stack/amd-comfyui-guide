# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

People who own an AMD Radeon GPU and want ComfyUI image generation to work. They
arrive from a failed install or a search for "ComfyUI AMD", usually on a low-VRAM
card (8 GB class) and on either Windows or Ubuntu. Their job: get from a bare
driver to a first image, then know which features will actually run on their card.

## Product Purpose

A tutorial-first guide to running ComfyUI on AMD GPUs: installation on Windows and
on Ubuntu + ROCm, model placement, first image, the workflow library, and
troubleshooting. Success means a reader with an AMD card can follow the chapters in
order and end up generating images without having to interpret an experiment log.

## Positioning

Every step and every illustrated result comes from one measured machine, and each
result can be traced back to its own record. The product is the tutorial; the
evidence library exists to back the instructions, not to be the destination.

## Operating Context

- The reader is at a shell or PowerShell on their own machine; chapters are read in
  order (01 → 08).
- Two platforms: Windows 10/11 with the AMD multi-arch ROCm package, and Ubuntu
  22.04.5 + ROCm 7.14.
- Low-VRAM habits are part of the workflow: CPU VAE, staged encoding/sampling/
  decoding, split attention, 512 px as the default size.
- The repository ships the site (GitHub Pages), the tutorial sources, 268
  ready-to-use workflows, and the evidence that backs them.

## Capabilities and Constraints

- Eight tutorial chapters, 268 workflows (UI + API, installed as a library), 7 model
  families, a filterable plate gallery, and a feature report.
- The verified machine is RX 6650 XT (gfx1032), 8 GB VRAM, 16 GB RAM — a measured
  example, never presented as the supported set.
- Copy constraints: no unverifiable claims ("end to end", "all real", "no
  post-processing" are banned); the concrete card appears only in image captions,
  plate badges and evidence tables; body copy speaks about AMD GPUs and 8 GB-class
  VRAM.
- Every attempt is kept, including failures, with SHA-256 provenance; the public
  snapshot is hashed in `publication-manifest.json` and verified in CI.
- Self-hosted OFL font subsets, no runtime CDN, MIT license, static single-file
  pages with hand-written CSS/JS.
- The evidence block on the landing page is deliberately reduced to a one-line link band;
  the numbers stay on the report page and in the READMEs (the reader chose a
  tutorial-first site with a deliberately de-emphasised evidence library).
- Undecided: whether more model families get their own tutorial chapters.

## Brand Commitments

- Name: **AMD ComfyUI Guide** (repo `amd-comfyui-guide`); the earlier "Barely Comfy"
  name is retired and must not come back.
- Voice: quiet and documentary; Chinese is the primary language, with English in
  display type and section nouns.
- Copy rules: nouns over sentences for navigation and section heads; no
  self-narration of experiments; no hedging, no absolute claims.
- Visual identity: darkroom archive — near-black paper, bone ink, one gold accent,
  editorial serif display, monospace metadata.

## Evidence on Hand

- `evidence/` — per-trial API graphs, histories, outputs and SHA-256.
- `report/` — the feature report (40 features × platforms).
- `assets/gallery/manifest.json` — 40 plates, each with prompt, seed, steps, sampler
  and its report anchor.
- `publication-manifest.json` plus `.github/workflows/check-publication.yml` — the
  public snapshot is hashed and re-verified in CI.
- Real machine record: RX 6650 XT · 8 GB VRAM · 16 GB RAM · Windows 10 /
  Ubuntu 22.04.5 · ROCm 7.14 · PyTorch 2.12.0 · ComfyUI `ce1e922`.

## Product Principles

1. The tutorial is the product; evidence backs it, never the reverse.
2. Every claim needs a door: if a reader cannot open it and check it, it does not go
   on the page.
3. One machine is the evidence, not the audience — write for any AMD card and show
   the measured card only where the picture is.
4. Keep the failures on the record; they are the most useful part of a field report.
5. Quiet documentary voice: no self-congratulation, no hedging.

## Accessibility & Inclusion

- Text targets WCAG AA contrast; functional text ≥ 11 px, body copy ≥ 12 px.
- Keyboard focus is always visible; `prefers-reduced-motion` is honoured.
- Chinese-first reading with English display accents; all controls carry readable
  accessible names.
