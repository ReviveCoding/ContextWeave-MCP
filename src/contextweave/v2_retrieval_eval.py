"""GPU-qualified dense retrieval and reranking for the v2 qualification pilot."""

from __future__ import annotations

import gc
import hashlib
import json
import time
from typing import Any

import numpy as np
import torch
from sentence_transformers import SentenceTransformer
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from contextweave.evidence import ROOT, atomic_json, utc_now
from contextweave.retrieval import BM25, MODEL_REVISION, corpus
from contextweave.retrieval_eval import HF_ROOT, RERANKER_REVISION


def _tasks() -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in (ROOT / "benchmarks/v2_pilot_tasks.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line
    ]


def embed_queries(batch_size: int = 64) -> dict[str, Any]:
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA required for v2 BGE-M3 query embeddings")
    tasks = _tasks()
    model_path = HF_ROOT / "models--BAAI--bge-m3/snapshots" / MODEL_REVISION
    model = SentenceTransformer(str(model_path), device="cuda", trust_remote_code=False)
    torch.cuda.reset_peak_memory_stats()
    start = time.perf_counter()
    vectors = model.encode(
        [task["query"] for task in tasks],
        batch_size=batch_size,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    torch.cuda.synchronize()
    out_dir = ROOT / "evidence/retrieval_v2"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "bge_m3_queries.npy"
    np.save(path, vectors)
    receipt = {
        "timestamp_utc": utc_now(),
        "protocol_identity": "ContextWeave-v2-family-diverse-qualification",
        "task_manifest_sha256": hashlib.sha256(
            (ROOT / "benchmarks/v2_pilot_tasks.jsonl").read_bytes()
        ).hexdigest(),
        "model": "BAAI/bge-m3",
        "revision": MODEL_REVISION,
        "device": torch.cuda.get_device_name(0),
        "dtype": str(vectors.dtype),
        "backend": "sentence-transformers/torch",
        "batch_size": batch_size,
        "query_count": len(tasks),
        "elapsed_seconds": time.perf_counter() - start,
        "peak_vram_bytes": torch.cuda.max_memory_allocated(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "evidence_class": "Q",
    }
    atomic_json(out_dir / "bge_m3_queries_receipt.json", receipt)
    del model
    gc.collect()
    torch.cuda.empty_cache()
    return receipt


def rerank(batch_size: int = 24, candidate_k: int = 20) -> dict[str, Any]:
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA required for v2 BGE reranker")
    tasks = _tasks()
    docs = corpus()
    catalog_path = ROOT / "evidence/retrieval/bge_m3_catalog.npy"
    catalog_receipt = json.loads(
        (ROOT / "evidence/retrieval/bge_m3_catalog_receipt.json").read_text()
    )
    if hashlib.sha256(catalog_path.read_bytes()).hexdigest() != catalog_receipt["embedding_sha256"]:
        raise RuntimeError("catalog embedding identity changed")
    doc_vectors = np.load(catalog_path)
    query_vectors = np.load(ROOT / "evidence/retrieval_v2/bge_m3_queries.npy")
    if len(query_vectors) != len(tasks) or len(doc_vectors) != len(docs):
        raise RuntimeError("v2 embedding/corpus identity mismatch")
    bm25 = BM25([doc["text"] for doc in docs])
    model_path = HF_ROOT / "models--BAAI--bge-reranker-v2-m3/snapshots" / RERANKER_REVISION
    tokenizer = AutoTokenizer.from_pretrained(str(model_path), local_files_only=True)
    model = (
        AutoModelForSequenceClassification.from_pretrained(
            str(model_path), dtype=torch.bfloat16, local_files_only=True
        )
        .to("cuda")
        .eval()
    )
    torch.cuda.reset_peak_memory_stats()
    started = time.perf_counter()
    out_dir = ROOT / "evidence/retrieval_v2"
    path = out_dir / "rankings.jsonl"
    with path.open("w", encoding="utf-8") as output:
        for index, task in enumerate(tasks):
            lexical = bm25.scores(task["query"])
            dense = doc_vectors @ query_vectors[index]
            lexical_order = np.argsort(-lexical, kind="stable")
            dense_order = np.argsort(-dense, kind="stable")
            rrf = np.zeros(len(docs), dtype=np.float32)
            for rank, doc_index in enumerate(lexical_order):
                rrf[doc_index] += 1 / (61 + rank)
            for rank, doc_index in enumerate(dense_order):
                rrf[doc_index] += 1 / (61 + rank)
            hybrid_order = np.argsort(-rrf, kind="stable")
            candidate_indices = list(hybrid_order[:candidate_k])
            scores: list[float] = []
            for offset in range(0, len(candidate_indices), batch_size):
                chunk = candidate_indices[offset : offset + batch_size]
                batch = tokenizer(
                    [task["query"]] * len(chunk),
                    [docs[j]["text"] for j in chunk],
                    padding=True,
                    truncation=True,
                    max_length=512,
                    return_tensors="pt",
                ).to("cuda")
                with torch.inference_mode():
                    scores.extend(model(**batch).logits.float().reshape(-1).cpu().tolist())
            reranked = [
                candidate_indices[j]
                for j in sorted(
                    range(len(scores)),
                    key=lambda j: (-scores[j], docs[candidate_indices[j]]["id"]),
                )
            ]
            output.write(
                json.dumps(
                    {
                        "task_id": task["task_id"],
                        "reranked": [docs[j]["id"] for j in reranked],
                    },
                    sort_keys=True,
                )
                + "\n"
            )
            output.flush()
    torch.cuda.synchronize()
    receipt = {
        "timestamp_utc": utc_now(),
        "protocol_identity": "ContextWeave-v2-family-diverse-qualification",
        "task_manifest_sha256": hashlib.sha256(
            (ROOT / "benchmarks/v2_pilot_tasks.jsonl").read_bytes()
        ).hexdigest(),
        "reranker": "BAAI/bge-reranker-v2-m3",
        "revision": RERANKER_REVISION,
        "device": torch.cuda.get_device_name(0),
        "dtype": "bfloat16",
        "backend": "transformers/torch",
        "batch_size": batch_size,
        "candidate_k": candidate_k,
        "task_count": len(tasks),
        "elapsed_seconds": time.perf_counter() - started,
        "peak_vram_bytes": torch.cuda.max_memory_allocated(),
        "rankings_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "evidence_class": "Q",
    }
    atomic_json(out_dir / "rankings_receipt.json", receipt)
    return receipt


if __name__ == "__main__":
    print(json.dumps(embed_queries(), indent=2), flush=True)
    print(json.dumps(rerank(), indent=2), flush=True)
