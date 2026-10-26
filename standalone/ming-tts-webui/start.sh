#!/bin/bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if [ "$(id -u)" -eq 0 ]; then
  exec docker compose up -d --no-build
fi
exec sudo docker compose up -d --no-build
