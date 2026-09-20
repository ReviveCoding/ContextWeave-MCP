#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/wsl-gpu-env.sh"

echo "=== WSL ==="
uname -a

echo
echo "=== PYTHON ==="
command -v python3
python3 --version

echo
echo "=== CPU / MEMORY ==="
printf 'CPU_THREADS=%s\n' "$(nproc)"
free -h

echo
echo "=== GPU ==="
command -v nvidia-smi
nvidia-smi \
  --query-gpu=name,memory.total,memory.free,driver_version,temperature.gpu \
  --format=csv,noheader

echo
echo "=== WSL EXT4 FILESYSTEM ==="
df -h "$HOME"

echo
echo "PREPROMPT_WSL_PREFLIGHT=PASS"