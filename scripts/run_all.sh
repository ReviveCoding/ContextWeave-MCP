#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export UV_PROJECT_ENVIRONMENT=/home/bjw-0/.cache/contextweave-mcp/venv
uv run --frozen contextweave run-all
