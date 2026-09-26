# Reproduction guide

## Supported scope

This guide reproduces software-quality and release validation. It does not rerun B2, C1, retrieval, task generation, E07, or any protected experiment. Canonical scientific artifacts are hash-checked before release generation.

## Platform

- Windows repository: `C:\Users\bjw-0\Downloads\ContextWeave-MCP`
- WSL repository: `/mnt/c/Users/bjw-0/Downloads/ContextWeave-MCP`
- Native WSL environment: `/home/bjw-0/.cache/contextweave-mcp/venv`
- Distro: Ubuntu-22.04
- Python: locked 3.12 environment

## Environment creation

From PowerShell:

```powershell
./scripts/bootstrap.ps1
```

Equivalent WSL command:

```bash
cd /mnt/c/Users/bjw-0/Downloads/ContextWeave-MCP
UV_PROJECT_ENVIRONMENT=/home/bjw-0/.cache/contextweave-mcp/venv \
  uv sync --frozen --all-extras --all-groups --python 3.12 --link-mode copy
```

This uses `pyproject.toml` and `uv.lock`, includes the existing `gpu` extra and `dev` dependency group, and copies packages into native ext4 storage. Do not repair the damaged Windows-mounted `.venv` in place and do not change the NVIDIA driver or system CUDA installation.

## Environment verification

```bash
ENV=/home/bjw-0/.cache/contextweave-mcp/venv
$ENV/bin/python --version
$ENV/bin/python -c 'import torch, transformers, contextweave; print(torch.__file__); print(torch.__version__); print(hasattr(torch,"Tensor"), hasattr(torch,"LongTensor")); print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0)); print(transformers.__version__); print(contextweave.__file__)'
```

## Quality closure

```bash
cd /mnt/c/Users/bjw-0/Downloads/ContextWeave-MCP
bash scripts/quality_close.sh
```

The script runs Ruff format and lint checks, strict mypy, full pytest, receipt integrity validation, deterministic figure generation, release validation, package build, and clean-wheel import smoke. It uses CPU tests for software validation and does not pretend to rerun GPU experiments.

## Scientific evidence boundaries

V1 closed as `V1_PRE_FREEZE_INSUFFICIENT_POWER`. The original v2 E07 is preserved as `SUPERSEDED_INVALID_CALIBRATION`. Corrected E07 was calibrated but required 799 independent families and closed as `V2_PRE_FREEZE_INSUFFICIENT_POWER_CALIBRATED`. No protected access or freeze exists. The +13.06 percentage-point pilot difference is qualification-only; no efficacy, production, Amazon-internal, security-certification, or external-transfer claim is supported.
