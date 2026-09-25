#!/usr/bin/env bash
set -euo pipefail

repo=/mnt/c/Users/bjw-0/Downloads/ContextWeave-MCP
scratch=/home/bjw-0/.cache/contextweave-mcp
cd "$repo"
mkdir -p "$scratch"
export PYTHONPATH="$repo/src"
exec "$scratch/venv/bin/python" -u scripts/supervise_v2_pilot.py \
  >>"$scratch/v2_supervisor.log" 2>&1
