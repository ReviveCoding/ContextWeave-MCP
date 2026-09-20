"""The pilot must refuse changed GPU ownership before another batch."""

import pytest

from contextweave import model_pilot


def test_exclusive_gpu_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(model_pilot, "_gpu_compute_pids", lambda: {42})
    with pytest.raises(RuntimeError, match="GPU compute owners changed"):
        model_pilot._assert_exclusive_gpu_owner(set())
    model_pilot._assert_exclusive_gpu_owner({42})
    with pytest.raises(RuntimeError, match="GPU compute owners changed"):
        model_pilot._assert_exclusive_gpu_owner({43})
