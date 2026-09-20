#!/usr/bin/env bash
set -euo pipefail

export CONTEXTWEAVE_REPO="/mnt/c/Users/bjw-0/Downloads/ContextWeave-MCP"
export CONTEXTWEAVE_SCRATCH="/home/bjw-0/.cache/contextweave-mcp"

export CUDA_DEVICE_ORDER=PCI_BUS_ID
export CUDA_VISIBLE_DEVICES=0

export HF_HOME="$CONTEXTWEAVE_SCRATCH/huggingface"
export TORCH_HOME="$CONTEXTWEAVE_SCRATCH/torch"
export UV_CACHE_DIR="$CONTEXTWEAVE_SCRATCH/uv"
export XDG_CACHE_HOME="$CONTEXTWEAVE_SCRATCH/cache"
export TMPDIR="$CONTEXTWEAVE_SCRATCH/tmp"

export CONTEXTWEAVE_GPU_REQUIRED=1
export CONTEXTWEAVE_CPU_MODEL_FALLBACK=0
export CONTEXTWEAVE_GPU_OWNER_MODE=1

mkdir -p \
    "$HF_HOME" \
    "$TORCH_HOME" \
    "$UV_CACHE_DIR" \
    "$XDG_CACHE_HOME" \
    "$TMPDIR" \
    "$CONTEXTWEAVE_SCRATCH/data" \
    "$CONTEXTWEAVE_SCRATCH/models" \
    "$CONTEXTWEAVE_SCRATCH/evidence-staging"