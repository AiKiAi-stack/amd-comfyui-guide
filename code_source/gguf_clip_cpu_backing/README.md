# Experimental Linux GGUF CLIP CPU backing

This node retains the original CPU parameter storage before the first GPU load,
then restores it on a complete CPU unload. It avoids a new GPU-to-CPU allocation
for every weight. Only the CLIP patcher instance and its descendants use the
policy; the stock GGUF class and the older MODEL experiment remain unchanged.

Connect `CLIPLoaderGGUF → RetainGgufClipCpuBacking → TextEncodeQwenImage21`.
It is inactive when absent from the workflow. Enable it before the first load.
Use the recorded Linux source versions and the separate bounded phase runner in
`evidence/2026-10-24-ubuntu-followup/`; its default is also off.

LoRA, weight wrappers, hooks and object patches are refused at enable/load/unload.
The one exception is the pinned core CLIP's standard
`manual_cast_dtype=torch.float32` policy, which changes compute precision rather
than stored parameter values. Floating parameters' original gradient flags are
preserved. This is an inference experiment, without training support.

The cache keeps CPU storages alive for the lifetime of the model, including mmap
views; this trades retained backing storage for avoiding transient copies. No
partial residency is retained: a partial CPU unload request restores all weights
and reports the patcher's previously loaded bytes. This avoids another copy and
pin path during model switching. No promise is made about complete allocator-cache release, OOM
recovery, model editing, reference images, other model families or Windows.

`scripts/test_gguf_clip_cpu_backing.py` exercises the installed GGUF unpatch path
with a real Q4_K tensor on the GPU. `--baseline` is intentionally red when a fresh
CPU copy is attempted. The candidate checks repeated storage/hash preservation,
GPU allocation release, clone policy, inference tensor handling outside its
creation context, and rejection of unsupported patches. Small tests do not
replace the full model trials and their retained failures.
