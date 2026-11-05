import hashlib
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from contextweave import evidence


@pytest.mark.parametrize("size", [0, 13, 2 * 1024 * 1024 + 17])
def test_artifact_hash_avoids_file_sized_reads(tmp_path: Path, monkeypatch, size: int) -> None:
    content = b"x" * size
    path = tmp_path / "embedding.npy"
    path.write_bytes(content)
    monkeypatch.setattr(Path, "read_bytes", lambda self: pytest.fail("unbounded read"))
    assert evidence.file_sha256(path) == hashlib.sha256(content).hexdigest()


def test_source_fallback_keeps_path_and_content_hash_order(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "z.py").write_text("last")
    (source / "a.py").write_text("first")
    expected = hashlib.sha256(b"src/a.pyfirstsrc/z.pylast").hexdigest()
    monkeypatch.setattr(evidence, "ROOT", tmp_path)
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=1))
    monkeypatch.setattr(Path, "read_bytes", lambda self: pytest.fail("unbounded read"))
    assert evidence.source_identity() == "uncommitted-source-sha256:" + expected
