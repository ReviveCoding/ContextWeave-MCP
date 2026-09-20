"""E01 hardware and installed-runtime qualification."""

from __future__ import annotations

import platform
import subprocess
from importlib import metadata
from typing import Any

from contextweave.evidence import ROOT, atomic_json, record, utc_now


def qualify() -> dict[str, Any]:
    started = utc_now()
    package_names = ("mcp", "duckdb", "torch", "transformers", "sentence-transformers", "sqlglot")
    packages: dict[str, str | None] = {}
    for name in package_names:
        try:
            packages[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            packages[name] = None
    gpu = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=name,driver_version,memory.total,memory.used,temperature.gpu",
            "--format=csv,noheader,nounits",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    cuda: dict[str, Any] = {"available": False, "reason": "torch unavailable"}
    if packages["torch"]:
        import torch

        cuda = {
            "available": torch.cuda.is_available(),
            "torch_cuda_version": torch.version.cuda,
            "device_count": torch.cuda.device_count(),
        }
        if cuda["available"]:
            x = torch.arange(1024, device="cuda", dtype=torch.float32)
            y = (x * x).sum()
            torch.cuda.synchronize()
            cuda.update(
                {
                    "device": torch.cuda.get_device_name(0),
                    "dtype": "float32",
                    "test_sum": float(y.item()),
                    "max_memory_allocated_bytes": torch.cuda.max_memory_allocated(),
                }
            )
    result = {
        "timestamp_utc": utc_now(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "packages": packages,
        "nvidia_smi_exit_code": gpu.returncode,
        "nvidia_smi": gpu.stdout.strip() if gpu.returncode == 0 else gpu.stderr.strip(),
        "cuda": cuda,
        "device_backend": "CUDA" if cuda["available"] else "UNQUALIFIED",
    }
    rel = "evidence/qualification/environment.json"
    atomic_json(ROOT / rel, result)
    status = "PASS" if gpu.returncode == 0 and cuda["available"] and packages["mcp"] else "FAIL"
    record(
        "E01",
        "E01-environment",
        {"cuda_required": True},
        {},
        result,
        status,
        [rel],
        "Q",
        started,
        None if status == "PASS" else "CUDA and installed MCP v2 are required",
    )
    return result
