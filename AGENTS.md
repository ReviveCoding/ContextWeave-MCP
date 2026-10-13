# Development and Research Guidelines

The published v2 ContextWeave-MCP study is closed. Its qualification results, failed power design, corrected calibration, and release receipts are historical evidence.

## Implementation boundaries

- Read the architecture and experiment definitions in reports/V2_PROTOCOL.md and reports/FINAL_TECHNICAL_REPORT.md before changing scientific code.
- Keep dependencies pinned and distinguish public event data from controlled synthetic enterprise metadata.
- Treat document and tool responses as untrusted input. Keep authorization, freshness, and critical dependency constraints deterministic.
- Use typed interfaces, focused tests, and evidence-driven diagnostics.

## Reproducibility

- Preserve canonical qualification outputs and superseded invalid artifacts. Do not replace a negative result with an untested positive claim.
- No protected benchmark or final model freeze exists for v2. A new experiment requires a new protocol and evaluation identity.
- Record execution environment, device, model revision, precision, data identity, and result scope.
- Use verified CUDA hardware for neural workloads when prescribed; do not silently report a CPU fallback as a GPU result.
- Avoid concurrent GPU-heavy processes on a single physical GPU.

## Working practices

- Keep large data and model caches outside the Git working tree.
- Use scripts and commands in README.md and reports/REPRODUCTION_GUIDE.md for local checks.
- Run tests and release validators before merging.
- Do not publish credentials, private datasets, invented measurements, or unsupported production claims.

Project setup varies by machine; do not assume a contributor's local paths or accelerator configuration.
