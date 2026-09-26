#!/usr/bin/env bash
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
scratch_dir=/home/bjw-0/.cache/contextweave-mcp
mkdir -p "$scratch_dir"
export UV_PROJECT_ENVIRONMENT="$scratch_dir/venv"
cd "$repo_dir"
uv python install 3.12
uv sync --frozen --all-extras --all-groups --python 3.12 --link-mode copy
uv run --frozen python scripts/verify_release_environment.py
