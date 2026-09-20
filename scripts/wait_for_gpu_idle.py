"""Wait for a sustained idle interval on the one physical GPU."""

import argparse
import subprocess
import time


def gpu_pids() -> set[int]:
    result = subprocess.run(
        ["nvidia-smi", "--query-compute-apps=pid", "--format=csv,noheader"],
        text=True,
        capture_output=True,
        check=True,
    )
    return {int(line.strip()) for line in result.stdout.splitlines() if line.strip().isdigit()}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--idle-seconds", type=int, default=120)
    parser.add_argument("--max-wait-seconds", type=int, default=3600)
    args = parser.parse_args()
    if args.idle_seconds < 1 or args.max_wait_seconds < args.idle_seconds:
        raise ValueError("invalid wait duration")
    start = time.monotonic()
    idle_since = None
    last_pids: set[int] | None = None
    while time.monotonic() - start < args.max_wait_seconds:
        pids = gpu_pids()
        if pids != last_pids:
            print(f"GPU compute PIDs: {sorted(pids)}", flush=True)
            last_pids = pids
        if pids:
            idle_since = None
        else:
            if idle_since is None:
                idle_since = time.monotonic()
            if time.monotonic() - idle_since >= args.idle_seconds:
                print(f"GPU idle for {args.idle_seconds} seconds", flush=True)
                return
        time.sleep(10)
    raise TimeoutError("GPU did not remain idle during the wait window")


if __name__ == "__main__":
    main()
