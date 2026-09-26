# Contributing

Contributions that improve software quality, documentation, reproducibility, or clearly labeled exploratory analysis are welcome.

## Development checks

Use Python 3.12 and the locked CPU environment:

```bash
uv sync --locked --no-extra gpu --group dev
uv run ruff format --check src tests scripts
uv run ruff check src tests scripts
uv run mypy --strict src/contextweave
uv run python -m pytest -q
uv run python scripts/validate_release.py
uv run python scripts/validate_posthoc_v1.py
```

## Scientific governance

- Do not modify canonical B2, C1, calibrated E07, closure, or receipt artifacts.
- Do not relabel qualification or post-hoc evidence as confirmatory.
- Do not create protected tasks or freezes under the closed v2 identity.
- New scientific experiments require a new protocol identity and explicit evidence boundaries.
- Keep public data, controlled synthetic data, qualification, protected, exploratory, and external evidence separate.
- Preserve negative, null, interrupted, invalid, and superseded results.

## Pull requests

Explain the purpose, changed files, verification commands, and any effect on evidence or claims. Scientific changes must identify their protocol and evidence class. Never commit raw datasets, model weights, credentials, local caches, virtual environments, or machine-specific debug files.

No software license is currently granted. A contribution does not change that status unless the repository owner adopts an explicit license separately.
