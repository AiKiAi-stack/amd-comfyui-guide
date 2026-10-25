#!/usr/bin/env bash
set -euo pipefail
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
runtime_dir="${COMFY_RUNTIME:-$repo_dir/runtime/ubuntu}"
if [[ ! -r /dev/kfd || ! -w /dev/kfd ]]; then
    echo 'GPU unavailable: grant your user access to /dev/kfd before starting.' >&2
    exit 1
fi
cd "$runtime_dir"
exec .venv/bin/python -X faulthandler -u ComfyUI/main.py \
    --listen 127.0.0.1 --port 8188 --cpu-vae \
    --disable-async-offload --disable-dynamic-vram \
    --extra-model-paths-config "$runtime_dir/model-paths.yaml" "$@"
