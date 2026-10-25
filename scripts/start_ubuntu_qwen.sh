#!/usr/bin/env bash
set -euo pipefail
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
exec bash "$repo_dir/scripts/start_ubuntu.sh" \
    --fast-disk --reserve-vram 1.0 --use-split-cross-attention \
    --force-fp16 --force-upcast-attention "$@"
