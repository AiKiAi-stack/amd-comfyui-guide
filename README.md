<div align="center">

<img src="assets/banner.webp" alt="AMD ComfyUI Guide — ComfyUI on AMD, tested end to end" width="100%">

# AMD ComfyUI Guide

**ComfyUI on AMD — tested end to end.**

Step-by-step setup for Windows and Ubuntu, a tested feature catalog, ready-to-use
workflows, and every result documented on an RX 6650 XT (8 GB).

[English](README.md) · [简体中文](README.zh-CN.md)

[![Check tutorial snapshot](https://github.com/AiKiAi-stack/amd-comfyui-guide/actions/workflows/check-publication.yml/badge.svg)](https://github.com/AiKiAi-stack/amd-comfyui-guide/actions/workflows/check-publication.yml)
[![Latest release](https://img.shields.io/github/v/release/AiKiAi-stack/amd-comfyui-guide?label=release)](https://github.com/AiKiAi-stack/amd-comfyui-guide/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

</div>

---

## What this is

A deployment guide for running ComfyUI image generation on AMD Radeon GPUs, backed by a reproducible evidence set. It starts with a verified step-by-step setup on one machine — RX 6650 XT, 8 GB VRAM, Windows 10 and Ubuntu 22.04.5 + ROCm 7.14 — then documents 40 features across 7 model families: what worked, what partially worked, what failed, and why.

- **Verified hardware:** AMD Radeon RX 6650 XT (gfx1032) · 16 GB RAM
- **Verified stack:** Ubuntu 22.04.5 · ROCm 7.14 · PyTorch 2.12.0 · ComfyUI `ce1e922`
- **Audience:** anyone with an AMD GPU who wants to know whether a ComfyUI feature runs — and how

This is a single-machine field report, not an AMD compatibility list. For other cards, see the [AMD GPU support matrix](docs/tutorial/08-amd-matrix.md).

## Results

<!-- STATS:START -->
| Metric | Value |
|---|---:|
| Model families | 7 |
| Features tested | 40 |
| Linux verdicts | 21 pass · 18 partial · 1 fail |
| Platform records | 162 (95 Windows + 67 Linux) |
| Workflows | 268 UI + 268 API · 184 installed |
| Documented cases | 88 |
<!-- STATS:END -->

<img src="assets/features.webp" alt="Four real outputs generated on an RX 6650 XT: Qwen Image 2.1 Turbo, FLUX.2 Klein, Kroma Q2, MOSS SFT" width="100%">

Open the **[full report](https://aikiai-stack.github.io/amd-comfyui-guide/)** — 40 cards, each with input, prompt, real output, timing and verdict per platform.

## Quick start

1. **Check your hardware** — [hardware & versions](docs/tutorial/01-hardware.md). Not an RX 6650 XT? Read the [support matrix](docs/tutorial/08-amd-matrix.md) first.
2. **Install** — [Windows](docs/tutorial/02-windows-setup.md) or [Ubuntu + ROCm](docs/tutorial/03-ubuntu-rocm.md). Ubuntu is the only path verified from a fresh, independent environment.
3. **Generate your first image** — [first image](docs/tutorial/04-first-image.md), then pick a workflow from the [workflow library](docs/tutorial/06-workflows.md).

No GPU? Open the [report](https://aikiai-stack.github.io/amd-comfyui-guide/) — it needs no model weights.

## Download the workflow library

268 WebUI workflows plus matching API files, checked by real frontend import/export:

- **[Full bundle (~360 MiB)](https://github.com/AiKiAi-stack/amd-comfyui-guide/releases/download/model-feature-workflows-2026-10-26/model-feature-workflows.zip)** — includes input images and encoded conditioning
- **[Light bundle (~12 MiB)](https://github.com/AiKiAi-stack/amd-comfyui-guide/releases/download/model-feature-workflows-2026-10-26/model-feature-workflows-light.zip)** — workflows only; run the encoding step first

Install steps, naming rules and SHA gotchas: [workflow library](docs/tutorial/06-workflows.md).

## Tutorial

| Chapter | When to read it |
|---|---|
| [01 Hardware & versions](docs/tutorial/01-hardware.md) | confirm your GPU / OS / version combination |
| [02 Windows setup](docs/tutorial/02-windows-setup.md) | native AMD environment on Windows |
| [03 Ubuntu + ROCm](docs/tutorial/03-ubuntu-rocm.md) | the verified path, from a fresh environment |
| [04 First image](docs/tutorial/04-first-image.md) | prove the GPU actually renders |
| [05 Models](docs/tutorial/05-models.md) | download and place model weights |
| [06 Workflow library](docs/tutorial/06-workflows.md) | download, import and reproduce results |
| [07 Troubleshooting](docs/tutorial/07-troubleshooting.md) | init crashes, OOM, black or noisy images |
| [08 AMD support matrix](docs/tutorial/08-amd-matrix.md) | adapt the guide to another AMD card |

Full docs index: [docs/](docs/README.md).

## Evidence and how to read it

Every feature has its own case: prompt, workflow, output image, timing and verdict. "Workflow opens", "image renders", "target met" and "stable across runs" are recorded separately — they are not interchangeable, and failed or partial results are kept on purpose. See [evidence & privacy](docs/reference/evidence-and-privacy.md) and the [failure tracker](docs/reference/failure-tracker.md).

## Project layout

```
docs/         tutorial, reference, journal
evidence/     per-feature report, cases and platform records
workflows/    268 UI + API workflows, catalog and bundles
scripts/      install, replay, verification
environment/  pinned versions and hardware records
assets/       README and site visuals, built from real outputs
```

## Contributing

Reproductions on other AMD cards are the most useful contribution — bring input, prompt, workflow, output, timing and failure evidence. Read [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE). Third-party sources and upstream licensing: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
