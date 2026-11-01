<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/brand/mark.svg">
  <img src="assets/brand/mark-light.svg" alt="AMD ComfyUI Guide" width="220">
</picture>

# AMD ComfyUI Guide

**From driver to first image.**

Run ComfyUI on an AMD Radeon GPU. The chapters go from a bare driver to a first
image, and every result links back to its record.

[English](README.md) · [简体中文](README.zh-CN.md)

[![Check tutorial snapshot](https://github.com/AiKiAi-stack/amd-comfyui-guide/actions/workflows/check-publication.yml/badge.svg)](https://github.com/AiKiAi-stack/amd-comfyui-guide/actions/workflows/check-publication.yml)
[![Latest release](https://img.shields.io/github/v/release/AiKiAi-stack/amd-comfyui-guide?label=release)](https://github.com/AiKiAi-stack/amd-comfyui-guide/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

</div>

---

## Quick start

1. **Check what you have.** [Before you install](docs/tutorial/01-hardware.md) is a
   short check: your card's gfx code, its VRAM class and your OS decide which
   chapters apply. On a different AMD card, read the
   [support matrix](docs/tutorial/08-amd-matrix.md) first.
2. **Install.** [Windows](docs/tutorial/02-windows-setup.md) or
   [Ubuntu + ROCm](docs/tutorial/03-ubuntu-rocm.md). Ubuntu is the only path that
   was completed from a clean, independent environment.
3. **Get one image out.** Follow [first image](docs/tutorial/04-first-image.md), then
   pick a workflow from the [workflow library](docs/tutorial/06-workflows.md).

## Tutorial

Read the chapters in order.

| Chapter | When to read it |
|---|---|
| [01 Before you install](docs/tutorial/01-hardware.md) | decide whether the guide applies to your card |
| [02 Windows setup](docs/tutorial/02-windows-setup.md) | install on Windows 10 or 11 |
| [03 Ubuntu + ROCm](docs/tutorial/03-ubuntu-rocm.md) | install on Ubuntu, from a clean environment |
| [04 First image](docs/tutorial/04-first-image.md) | prove the GPU actually renders |
| [05 Models](docs/tutorial/05-models.md) | pick a model family and place the weights |
| [06 Workflow library](docs/tutorial/06-workflows.md) | download, import and reproduce a result |
| [07 Troubleshooting](docs/tutorial/07-troubleshooting.md) | init crashes, OOM, black or noisy images |
| [08 Adapt to another card](docs/tutorial/08-amd-matrix.md) | what changes on a card other than the measured one |

The full index is in [docs/](docs/README.md).

## Workflow library

268 WebUI workflows, each with a matching API file, checked by importing and
exporting every one in the real ComfyUI frontend. Two bundles:

- [Full, about 360 MiB](https://github.com/AiKiAi-stack/amd-comfyui-guide/releases/download/model-feature-workflows-2026-10-26/model-feature-workflows.zip):
  workflows, input images and the checked encoding files.
- [Light, about 12 MiB](https://github.com/AiKiAi-stack/amd-comfyui-guide/releases/download/model-feature-workflows-2026-10-26/model-feature-workflows-light.zip):
  workflows only; run the encoding step yourself.

Install steps, file naming and the SHA caveats are in the
[workflow library chapter](docs/tutorial/06-workflows.md).

## Results

<!-- STATS:START -->
| Metric | Value |
|---|---:|
| Model families | 7 |
| Features documented | 40 |
| Platform records | 162 (95 Windows + 67 Linux) |
| Workflows | 268 UI + 268 API · 184 installed |
| Documented cases | 88 |
<!-- STATS:END -->

<img src="assets/features.webp" alt="Four real outputs from the workflow library: Qwen Image 2.1 Turbo, FLUX.2 Klein, Kroma Q2, MOSS SFT" width="100%">

The [full report](https://aikiai-stack.github.io/amd-comfyui-guide/) has 40 cards,
each with the input, prompt, real output, timing and per-platform verdict. It needs
no model weights, so it also works if you only want to see what the models produce.

## Evidence and how to read it

Every number here was measured on one machine. Its configuration, platform coverage
and pinned versions are recorded in [test machine](docs/reference/test-machine.md).
That card is the evidence, not the audience: this is a single-machine field report,
not an AMD compatibility list, so check the
[support matrix](docs/tutorial/08-amd-matrix.md) before assuming a result transfers.

Four things are recorded separately: the workflow opens, an image comes out, the
target is met, and the run is stable across repeats. They are not interchangeable.
Failed and partial results stay on the record on purpose. Start with
[evidence and privacy](docs/reference/evidence-and-privacy.md) and the
[failure tracker](docs/reference/failure-tracker.md). The raw experimental trail is
archived in [barely-comfy-evidence](https://github.com/AiKiAi-stack/barely-comfy-evidence)
with a SHA-256 manifest.

## Project layout

```
docs/         tutorial, reference, journal
evidence/     per-feature report, cases and platform records
workflows/    268 UI + API workflows, catalog and bundles
scripts/      install, replay, verification
environment/  pinned versions and hardware records
assets/       README and site visuals, built from real outputs
```

## Related

- **[ming-tts-webui](https://github.com/AiKiAi-stack/ming-tts-webui)**: a local
  Ming-3.0-TTS speech workbench (Gradio + FastAPI on AMD ROCm), kept in its own
  repository.

## Contributing

The most useful contribution is a reproduction on another AMD card. Bring the input,
prompt, workflow, output, timing and the failure evidence. Read
[CONTRIBUTING.md](CONTRIBUTING.md) first.

## License

[MIT](LICENSE). Third-party sources and upstream licensing are listed in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
