# FLUX.2 Klein 4B distilled API recipes

Source snapshot: local installed ComfyUI workflow template JSON under `.venv/Lib/site-packages/comfyui_workflow_templates_json/templates/` (text-to-image and `image_flux2_klein_image_edit_4b_distilled.json`). The API files flatten the relevant nested subgraphs into ComfyUI prompt-API format. They are preparation artifacts only; no service or GPU was run.

The distilled path keeps the template's `KSamplerSelect(euler)` -> `SamplerCustomAdvanced` path, `Flux2Scheduler(steps=4, width, height)`, `CFGGuider(cfg=1)` and `ConditioningZeroOut` negative-conditioning wiring. The local text-to-image workflow contains both base and distilled variants; the distilled subgraph is marked mode 4 in the UI template, so this API graph extracts that branch. The edit template similarly includes a one-image active graph and a two-image example marked mode 4; both were flattened from the distilled edit subgraphs. This local snapshot uses `CFGGuider`, not `BasicGuider`; the connection follows the actual installed template.

All workflows use `UNETLoader(unet_name=flux-2-klein-4b-fp8.safetensors, weight_dtype=default)`, `CLIPLoader(qwen_3_4b.safetensors, type=flux2, device=cpu)`, and `VAELoader(flux2-vae.safetensors)`. The local T2I distilled graph's placeholder filename is `flux-2-klein-4b.safetensors`; the loader value here is set to the requested/downloaded FP8 filename, while the node graph and 4-step schedule remain those of the distilled branch.

## Files

- `01_t2i_512.api.json`: 512×512, template T2I prompt retained.
- `02_single_edit_025mp.api.json`: one reference image; `ImageScaleToTotalPixels` set from the template's 1.0 MP to 0.25 MP.
- `03_dual_edit_025mp.api.json`: handbag first, logo second; each reference independently scales to 0.25 MP.
- `bindings.json`: prompt, SaveImage, LoadImage, and RandomNoise node IDs, image ordering, model names, and asset URLs.

## Resolution and assets

T2I sets the latent and scheduler directly to 512×512. Editing retains the official template's `ImageScaleToTotalPixels -> GetImageSize -> Flux2Scheduler/EmptyFlux2LatentImage` wiring. The template uses 1.0 MP; this recipe uses 0.25 MP. Scaling preserves each reference's aspect ratio, so the actual output width/height follow the scaled first reference through `GetImageSize` rather than being forced to 512×512. For a square reference this is approximately 512×512; non-square inputs produce different dimensions. In the dual-reference graph, image1 (handbag) controls output size; image2 (logo) is independently scaled and encoded as the second reference.

The installed media packages do not contain `handbag_white.png` or `comfy_logo_blue.png`. No image has been downloaded or copied. The official Comfy sources are [handbag_white.png](https://raw.githubusercontent.com/Comfy-Org/workflow_templates/main/input/handbag_white.png) and [comfy_logo_blue.png](https://raw.githubusercontent.com/Comfy-Org/workflow_templates/main/input/comfy_logo_blue.png). The API graphs refer to the original filenames in the `ComfyUI/input/` root. The installed `LoadImage` node enumerates root-level input files, so the parent runner should fetch/copy them there (current input root has no filename collision) or substitute the names.
