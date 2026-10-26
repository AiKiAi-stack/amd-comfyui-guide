#!/bin/bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
definition=$(mktemp)
trap 'rm -f -- "$definition"' EXIT
docker compose build --print > "$definition"
if [ "$(id -u)" -eq 0 ]; then
  docker buildx bake --allow network.host -f "$definition" --load
else
  sudo docker buildx bake --allow network.host -f "$definition" --load
fi
