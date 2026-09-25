"""Fail-closed GPU ownership queries and sustained verified-idle waiting."""

from __future__ import annotations

import argparse
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class GpuSnapshot:
    status: Literal["KNOWN", "GPU_STATE_UNKNOWN"]
    owners: frozenset[int]
    returncode: int
    stdout: str
    stderr: str


class GpuStateUnknown(RuntimeError):
    """GPU ownership could not be established, so work must fail closed."""


def query_gpu_state(
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> GpuSnapshot:
    result = runner(
        [
            "nvidia-smi",
            "--query-compute-apps=pid,process_name",
            "--format=csv,noheader,nounits",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return GpuSnapshot(
            "GPU_STATE_UNKNOWN",
            frozenset(),
            result.returncode,
            result.stdout,
            result.stderr,
        )
    owners: set[int] = set()
    for raw_line in result.stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        pid_text, separator, _process_name = line.partition(",")
        if not separator or not pid_text.strip().isdigit():
            return GpuSnapshot(
                "GPU_STATE_UNKNOWN",
                frozenset(),
                result.returncode,
                result.stdout,
                result.stderr,
            )
        # A numeric PID is an owner even when WSL reports its name as [Not Found].
        owners.add(int(pid_text.strip()))
    return GpuSnapshot("KNOWN", frozenset(owners), result.returncode, result.stdout, result.stderr)


def gpu_pids() -> set[int]:
    """Compatibility API for model-side ownership checks; unknown fails closed."""
    snapshot = query_gpu_state()
    if snapshot.status == "GPU_STATE_UNKNOWN":
        raise GpuStateUnknown(
            f"GPU_STATE_UNKNOWN returncode={snapshot.returncode} stderr={snapshot.stderr.strip()!r}"
        )
    return set(snapshot.owners)


def wait_for_verified_idle(
    idle_seconds: float = 120,
    poll_seconds: float = 10,
    max_wait_seconds: float | None = None,
    *,
    query: Callable[[], GpuSnapshot] = query_gpu_state,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
    log: Callable[[str], None] = lambda message: print(message, flush=True),
) -> None:
    if idle_seconds <= 0 or poll_seconds <= 0:
        raise ValueError("idle and poll durations must be positive")
    if max_wait_seconds is not None and max_wait_seconds < idle_seconds:
        raise ValueError("max wait must be at least the idle duration")
    started = clock()
    idle_since: float | None = None
    previous_owners: frozenset[int] | None = None
    unknown_attempts = 0
    while max_wait_seconds is None or clock() - started < max_wait_seconds:
        snapshot = query()
        if snapshot.status == "GPU_STATE_UNKNOWN":
            idle_since = None
            previous_owners = None
            unknown_attempts += 1
            delay = min(poll_seconds * (2 ** (unknown_attempts - 1)), 30.0)
            log(
                "GPU_STATE_UNKNOWN "
                f"returncode={snapshot.returncode} stdout={snapshot.stdout.strip()!r} "
                f"stderr={snapshot.stderr.strip()!r}; retry_seconds={delay:g}"
            )
            sleep(delay)
            continue

        unknown_attempts = 0
        owners = snapshot.owners
        if owners != previous_owners:
            log(f"GPU compute PIDs: {sorted(owners)}")
            previous_owners = owners
        if owners:
            idle_since = None
        elif idle_since is None:
            idle_since = clock()
        elif clock() - idle_since >= idle_seconds:
            log(f"GPU verified idle for {idle_seconds:g} seconds")
            return
        sleep(poll_seconds)
    raise TimeoutError("GPU did not remain verifiably idle during the wait window")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--idle-seconds", type=float, default=120)
    parser.add_argument("--poll-seconds", type=float, default=10)
    parser.add_argument("--max-wait-seconds", type=float, default=3600)
    args = parser.parse_args()
    wait_for_verified_idle(args.idle_seconds, args.poll_seconds, args.max_wait_seconds)


if __name__ == "__main__":
    main()
