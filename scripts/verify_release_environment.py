"""Verify the release environment without rewriting E01 scientific evidence."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import sys
from datetime import UTC, datetime
from pathlib import Path

import torch
import transformers

import contextweave

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    cuda_available = torch.cuda.is_available()
    result = {
        "timestamp_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "evidence_class": "D",
        "purpose": "release environment repair; does not replace E01 scientific evidence",
        "python_version": platform.python_version(),
        "python_executable": os.path.realpath(sys.executable),
        "torch_import_path": torch.__file__,
        "torch_version": torch.__version__,
        "torch_has_tensor": hasattr(torch, "Tensor"),
        "torch_has_long_tensor": hasattr(torch, "LongTensor"),
        "torch_cuda_version": torch.version.cuda,
        "cuda_available": cuda_available,
        "cuda_device_name": torch.cuda.get_device_name(0) if cuda_available else None,
        "transformers_version": transformers.__version__,
        "contextweave_import_path": contextweave.__file__,
        "pyproject_sha256": sha256(ROOT / "pyproject.toml"),
        "uv_lock_sha256": sha256(ROOT / "uv.lock"),
    }
    valid = (
        result["python_version"].startswith("3.12.")
        and result["torch_has_tensor"]
        and result["torch_has_long_tensor"]
        and cuda_available
        and result["cuda_device_name"] == "NVIDIA GeForce RTX 4090 Laptop GPU"
    )
    result["status"] = "PASS" if valid else "FAIL"
    target = ROOT / "evidence/quality/release_environment.json"
    temporary = target.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(target)
    print(json.dumps(result, indent=2, sort_keys=True))
    if not valid:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
