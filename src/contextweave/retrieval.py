"""Catalog corpus and GPU-qualified dense retrieval artifacts."""

from __future__ import annotations

import hashlib
import json
import math
import re
import time
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

from contextweave.catalog import METRICS
from contextweave.evidence import ROOT, atomic_json, utc_now
from contextweave.warehouse import BASE, CUSTOM

MODEL_REVISION = "5617a9f61b028005a4858fdac845db406aefb181"


def corpus() -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    for table, custom in CUSTOM.items():
        names = [column.split()[0] for column in (*BASE, *custom)]
        docs.append(
            {
                "id": f"TABLE:{table}",
                "kind": "TABLE",
                "text": f"Table {table}. Columns: {', '.join(names)}. Account and tenant scoped unless a public semantic object.",
            }
        )
        for name in names:
            docs.append(
                {
                    "id": f"COLUMN:{table}.{name}",
                    "kind": "COLUMN",
                    "text": f"Column {table}.{name}. Member of table {table}.",
                }
            )
    for metric in METRICS:
        docs.append(
            {
                "id": metric.metric_id,
                "kind": "METRIC",
                "text": f"Metric {metric.canonical_name}; aliases {', '.join(metric.aliases)}; exact formula {metric.formula}; unit {metric.unit}; requires {', '.join(metric.required_columns)}.",
            }
        )
    return docs


def save_corpus() -> dict[str, Any]:
    docs = corpus()
    path = ROOT / "evidence/retrieval/catalog_corpus.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(doc, sort_keys=True) + "\n" for doc in docs), encoding="utf-8"
    )
    manifest = {
        "created_at_utc": utc_now(),
        "document_count": len(docs),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "provenance": "T3 controlled warehouse schema and governed metric catalog",
    }
    atomic_json(ROOT / "evidence/retrieval/catalog_corpus_manifest.json", manifest)
    return manifest


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.casefold().replace("_", " "))


class BM25:
    def __init__(self, texts: list[str], k1: float = 1.5, b: float = 0.75) -> None:
        self.term_counts = [Counter(_tokens(text)) for text in texts]
        self.lengths = [sum(c.values()) for c in self.term_counts]
        self.avg_length = sum(self.lengths) / max(len(self.lengths), 1)
        self.document_frequency = Counter(term for c in self.term_counts for term in c)
        self.n = len(texts)
        self.k1 = k1
        self.b = b

    def scores(self, query: str) -> np.ndarray[Any, Any]:
        result = np.zeros(self.n, dtype=np.float32)
        for term in set(_tokens(query)):
            df = self.document_frequency[term]
            if not df:
                continue
            idf = math.log(1 + (self.n - df + 0.5) / (df + 0.5))
            for index, counts in enumerate(self.term_counts):
                freq = counts[term]
                if freq:
                    norm = self.k1 * (1 - self.b + self.b * self.lengths[index] / self.avg_length)
                    result[index] += idf * freq * (self.k1 + 1) / (freq + norm)
        return result


def embed_catalog(batch_size: int = 64) -> dict[str, Any]:
    import torch
    from sentence_transformers import SentenceTransformer

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA required: no CPU fallback for BGE-M3 embedding")
    docs = corpus()
    cache = (
        Path("/home/bjw-0/.cache/contextweave-mcp/hf/hub/models--BAAI--bge-m3/snapshots")
        / MODEL_REVISION
    )
    if not cache.exists():
        raise FileNotFoundError(cache)
    started = time.perf_counter()
    model = SentenceTransformer(str(cache), device="cuda", trust_remote_code=False)
    vectors = model.encode(
        [doc["text"] for doc in docs],
        batch_size=batch_size,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    torch.cuda.synchronize()
    elapsed = time.perf_counter() - started
    out = ROOT / "evidence/retrieval/bge_m3_catalog.npy"
    out.parent.mkdir(parents=True, exist_ok=True)
    np.save(out, vectors)
    receipt = {
        "timestamp_utc": utc_now(),
        "model": "BAAI/bge-m3",
        "revision": MODEL_REVISION,
        "device": torch.cuda.get_device_name(0),
        "backend": "sentence-transformers/torch",
        "dtype": str(vectors.dtype),
        "batch_size": batch_size,
        "document_count": len(docs),
        "dimension": int(vectors.shape[1]),
        "elapsed_seconds": elapsed,
        "peak_vram_bytes": torch.cuda.max_memory_allocated(),
        "embedding_sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
        "evidence_class": "Q",
    }
    atomic_json(ROOT / "evidence/retrieval/bge_m3_catalog_receipt.json", receipt)
    return receipt
