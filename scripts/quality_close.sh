#!/usr/bin/env bash
set -euo pipefail
repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
scratch_dir=/home/bjw-0/.cache/contextweave-mcp
export UV_PROJECT_ENVIRONMENT="$scratch_dir/venv"
cd "$repo_dir"

uv run --frozen python scripts/verify_release_environment.py
uv run --frozen ruff format --check src tests scripts
uv run --frozen ruff check src tests scripts
uv run --frozen mypy src/contextweave
uv run --frozen pytest -q --junitxml="$scratch_dir/pytest-release.xml"
uv run --frozen python scripts/audit_receipts.py
uv run --frozen python scripts/generate_release_artifacts.py
uv run --frozen python scripts/validate_release.py

rm -rf "$scratch_dir/dist" "$scratch_dir/wheel-smoke"
uv lock --check
uv build --out-dir "$scratch_dir/dist"
uv venv --python 3.12 --clear "$scratch_dir/wheel-smoke"
wheel="$(find "$scratch_dir/dist" -maxdepth 1 -name '*.whl' -print -quit)"
uv pip install --python "$scratch_dir/wheel-smoke/bin/python" --no-deps "$wheel"
"$scratch_dir/wheel-smoke/bin/python" -c 'import contextweave; print(contextweave.__file__)'
uv run --frozen python scripts/record_release_closure.py \
  --wheel "$wheel" --junit "$scratch_dir/pytest-release.xml"
uv run --frozen python scripts/audit_receipts.py
uv run --frozen python scripts/validate_release.py
