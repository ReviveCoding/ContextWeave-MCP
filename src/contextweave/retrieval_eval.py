"""Development retrieval qualification; no TaskSuccess claim without Qwen execution."""

from __future__ import annotations

import gc
import hashlib
import json
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
from sentence_transformers import SentenceTransformer
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from contextweave.evidence import ROOT, atomic_json, utc_now
from contextweave.retrieval import BM25, MODEL_REVISION, corpus

HF_ROOT = Path("/home/bjw-0/.cache/contextweave-mcp/hf/hub")
RERANKER_REVISION = "953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e"


def _tasks() -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in (ROOT / "benchmarks/pilot_programmatic.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line
    ]


def embed_queries(batch_size: int = 64) -> dict[str, Any]:
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA required for BGE-M3 query embeddings")
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
    elapsed = time.perf_counter() - start
    path = ROOT / "evidence/retrieval/bge_m3_pilot_queries.npy"
    np.save(path, vectors)
    receipt = {
        "timestamp_utc": utc_now(),
        "model": "BAAI/bge-m3",
        "revision": MODEL_REVISION,
        "device": torch.cuda.get_device_name(0),
        "dtype": str(vectors.dtype),
        "backend": "sentence-transformers/torch",
        "batch_size": batch_size,
        "query_count": len(tasks),
        "elapsed_seconds": elapsed,
        "peak_vram_bytes": torch.cuda.max_memory_allocated(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "evidence_class": "Q",
    }
    atomic_json(ROOT / "evidence/retrieval/bge_m3_pilot_queries_receipt.json", receipt)
    del model
    gc.collect()
    torch.cuda.empty_cache()
    return receipt


def rerank_pilot(batch_size: int = 24, candidate_k: int = 20) -> dict[str, Any]:
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA required for BGE reranker")
    tasks = _tasks()
    docs = corpus()
    bm25 = BM25([doc["text"] for doc in docs])
    doc_vectors = np.load(ROOT / "evidence/retrieval/bge_m3_catalog.npy")
    query_vectors = np.load(ROOT / "evidence/retrieval/bge_m3_pilot_queries.npy")
    if len(query_vectors) != len(tasks) or len(doc_vectors) != len(docs):
        raise ValueError("embedding/corpus identity mismatch")
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
    path = ROOT / "evidence/retrieval/pilot_rankings.jsonl"
    with path.open("w", encoding="utf-8") as out:
        for index, task in enumerate(tasks):
            lexical = bm25.scores(task["query"])
            dense = doc_vectors @ query_vectors[index]
            lexical_order = np.argsort(-lexical, kind="stable")
            dense_order = np.argsort(-dense, kind="stable")
            rrf = np.zeros(len(docs), dtype=np.float32)
            for rank, doc_index in enumerate(lexical_order):
                rrf[doc_index] += 1 / (60 + rank + 1)
            for rank, doc_index in enumerate(dense_order):
                rrf[doc_index] += 1 / (60 + rank + 1)
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
                    logits = model(**batch).logits.float().reshape(-1)
                scores.extend(logits.cpu().tolist())
            reranked = [
                candidate_indices[j]
                for j in sorted(
                    range(len(scores)), key=lambda j: (-scores[j], docs[candidate_indices[j]]["id"])
                )
            ]
            row = {
                "task_id": task["task_id"],
                "bm25": [docs[j]["id"] for j in lexical_order[:candidate_k]],
                "dense": [docs[j]["id"] for j in dense_order[:candidate_k]],
                "hybrid": [docs[j]["id"] for j in hybrid_order[:candidate_k]],
                "reranked": [docs[j]["id"] for j in reranked],
            }
            out.write(json.dumps(row, sort_keys=True) + "\n")
            out.flush()
    torch.cuda.synchronize()
    receipt = {
        "timestamp_utc": utc_now(),
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
    atomic_json(ROOT / "evidence/retrieval/pilot_rankings_receipt.json", receipt)
    return receipt


def evaluate_recall(k: int = 20) -> dict[str, Any]:
    tasks = {task["task_id"]: task for task in _tasks()}
    rankings = [
        json.loads(line)
        for line in (ROOT / "evidence/retrieval/pilot_rankings.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line
    ]
    result: dict[str, Any] = {}
    for method in ("bm25", "dense", "hybrid", "reranked"):
        recalls = []
        for row in rankings:
            task = tasks[row["task_id"]]
            required = {f"TABLE:{table}" for table in task["required_tables"]}
            required |= {f"COLUMN:{column}" for column in task["required_columns"]}
            required |= set(task["required_metrics"])
            recalls.append(len(required & set(row[method][:k])) / len(required))
        result[method] = {
            "mean_required_object_recall_at_k": sum(recalls) / len(recalls),
            "full_dependency_recall_at_k": sum(x == 1 for x in recalls) / len(recalls),
        }
    result.update(
        {
            "task_count": len(rankings),
            "k": k,
            "evidence_class": "Q",
            "scope": "retrieval only; not task success",
        }
    )
    atomic_json(ROOT / "evidence/retrieval/pilot_recall.json", result)
    return result


if __name__ == "__main__":
    print(json.dumps(embed_queries(), indent=2), flush=True)
    print(json.dumps(rerank_pilot(), indent=2), flush=True)
    print(json.dumps(evaluate_recall(), indent=2), flush=True)
