# Failure analysis

## Scientific failures and gates

1. **V1 family diversity:** v1 had only six semantic families. Its conservative family-sensitivity diagnostic required 3,165 tasks, above the 600-task ceiling. It closed as `V1_PRE_FREEZE_INSUFFICIENT_POWER`.
2. **Original v2 E07 calibration:** clipping and Dirichlet pseudocount shrinkage shifted the intended null-boundary mean to a positive value. The resulting 0.25–0.41 apparent Type I error was invalid. The implementation and artifacts are preserved as `SUPERSEDED_INVALID_CALIBRATION`.
3. **Corrected v2 E07:** independent 100,000-replicate checks restored nominal behavior for the t reference and homogeneous binary case. The observed heterogeneous stress case was conservative. The corrected analysis required 799 independent families and found maximum feasible simulated power 0.1165, so v2 closed as `V2_PRE_FREEZE_INSUFFICIENT_POWER_CALIBRATED`.

## Infrastructure interruptions

Reboots interrupted v1 E06, v2 B2, and supervisor operation. Durable JSONL checkpoints and receipts preserved completed work. A transient WSL `nvidia-smi` exit 255 was classified as `GPU_STATE_UNKNOWN`; the guard fails closed, resets the idle timer, and preserves checkpoints. These interruptions are infrastructure evidence rather than scientific failures.

The project-local Windows-mounted `.venv` later became incomplete and exposed a namespace-only `torch` package. Release repair uses a clean native WSL ext4 environment from `uv.lock`; it does not alter model outcomes or scientific evidence.

## Invalid and superseded evidence

Invalid-gold outputs, alias-sensitive pilot outputs, partial checkpoints, and the original v2 E07 remain separate from canonical corrected outcomes. None is reused as a corrected or protected result.

## Unavailable downstream analyses

E08–E25, including protected baselines, token frontiers, end-to-end agent evaluation, cache experiments, security experiments, OOD stress, systems benchmarking, ablations, Spider2 execution, locked final evaluation, and post-audit slicing, are `NOT RUN / GATED`. Their figures explicitly show that status.

## Claim boundary

The observed +13.06 percentage-point v2 difference is qualification evidence only. It is not evidence of efficacy, production value, Amazon-internal performance, production-advertiser impact, security certification, or external transfer.
