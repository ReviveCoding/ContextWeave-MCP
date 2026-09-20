"""Resumable E06 pilot inference on one CUDA owner process."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import time
from pathlib import Path
from typing import Any, cast

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from contextweave.benchmark import normalized_hash
from contextweave.context_planner import plan_context
from contextweave.evidence import ROOT, atomic_json, record, utc_now
from contextweave.retrieval import BM25, corpus
from contextweave.security import Claims, SecurityError, run_readonly_sql

QWEN_REVISION = "1cfa9a7208912126459214e8b04321603b3df60c"
MODEL_DIR = (
    Path("/home/bjw-0/.cache/contextweave-mcp/hf/hub/models--Qwen--Qwen3-4B/snapshots")
    / QWEN_REVISION
)
SYSTEM_PROMPT = (
    "You write one safe DuckDB SELECT query for a governed analytical warehouse. "
    "Return SQL only, without markdown or explanation. Use the supplied schema and exact metric formulas. "
    "Never request files, extensions, or network access. If the request lacks enough context, write ABSTAIN."
)


def _sql_from_text(text: str) -> str | None:
    cleaned = text.strip().replace("```sql", "").replace("```", "").strip()
    if cleaned.upper().startswith("SELECT "):
        return cleaned.split(";")[0].strip()
    match = re.search(r"(?is)\bSELECT\b.+?(?:;|$)", cleaned)
    return match.group(0).rstrip(";").strip() if match else None


def _context_for(
    query: str,
    docs: list[dict[str, Any]],
    bm25: BM25,
    doc_token_costs: list[int],
    tokenizer: Any,
    budget: int = 1024,
) -> tuple[str, int]:
    scores = bm25.scores(query)
    selected = []
    used = 0
    for index in sorted(range(len(docs)), key=lambda i: (-float(scores[i]), docs[i]["id"])):
        text = docs[index]["text"]
        cost = doc_token_costs[index] + 2
        if used + cost <= budget:
            selected.append(text)
            used += cost
        if used >= budget:
            break
    while selected:
        context = "\n".join(selected)
        exact_tokens = len(tokenizer.encode(context, add_special_tokens=False))
        if exact_tokens <= budget:
            return context, exact_tokens
        selected.pop()
    return "", 0


def _atomic_checkpoint(path: Path, rows: list[dict[str, Any]]) -> None:
    """Replace the whole small pilot checkpoint so a reboot cannot leave a torn row."""
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")
        f.flush()
        os.fsync(f.fileno())
        temporary = Path(f.name)
    os.replace(temporary, path)


def run_pilot() -> dict[str, Any]:
    if not torch.cuda.is_available():
        raise RuntimeError("GPU-designated pilot cannot run on CPU")
    if not MODEL_DIR.exists():
        raise FileNotFoundError(MODEL_DIR)
    started = utc_now()
    task_path = ROOT / "benchmarks/pilot_programmatic.jsonl"
    task_identity = hashlib.sha256(task_path.read_bytes()).hexdigest()
    frozen_manifest = json.loads(
        (ROOT / "benchmarks/pilot_manifest.json").read_text(encoding="utf-8")
    )
    if task_identity != frozen_manifest["task_file_sha256"]:
        raise RuntimeError("frozen pilot task identity changed")
    tasks = [
        json.loads(line) for line in task_path.read_text(encoding="utf-8").splitlines() if line
    ]
    method = os.environ.get("CONTEXTWEAVE_PILOT_METHOD", "B2")
    if method not in {"B2", "C1"}:
        raise ValueError("pilot method must be B2 or C1")
    out = ROOT / f"evidence/pilot/{method.lower()}_qwen3_4b.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    task_ids = [task["task_id"] for task in tasks]
    if len(task_ids) != len(set(task_ids)) or len(tasks) != frozen_manifest["task_count"]:
        raise RuntimeError("frozen pilot task IDs are invalid")
    existing: dict[str, Any] = {}
    if out.exists():
        for line in out.read_text(encoding="utf-8").splitlines():
            if line:
                item = json.loads(line)
                if item["task_manifest_sha256"] != task_identity:
                    raise RuntimeError(
                        "pilot checkpoint task identity changed; preserve old protocol separately"
                    )
                if item["task_id"] not in task_ids or item["task_id"] in existing:
                    raise RuntimeError("pilot checkpoint contains an unknown or duplicate task ID")
                if item["method"] != method or item["model_revision"] != QWEN_REVISION:
                    raise RuntimeError("pilot checkpoint model or method identity changed")
                existing[item["task_id"]] = item
    docs = corpus()
    bm25 = BM25([doc["text"] for doc in docs])
    rankings: dict[str, list[str]] = {}
    if method == "C1":
        rankings = {
            row["task_id"]: row["reranked"]
            for row in (
                json.loads(line)
                for line in (ROOT / "evidence/retrieval/pilot_rankings.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
                if line
            )
        }
    torch.cuda.reset_peak_memory_stats()
    load_start = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(str(MODEL_DIR), local_files_only=True)
    tokenizer.padding_side = "left"
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    doc_token_costs = [len(tokenizer.encode(doc["text"], add_special_tokens=False)) for doc in docs]
    model: Any = AutoModelForCausalLM.from_pretrained(
        str(MODEL_DIR), dtype=torch.bfloat16, device_map="cuda", local_files_only=True
    )
    model.eval()
    torch.cuda.synchronize()
    load_seconds = time.perf_counter() - load_start
    warehouse = json.loads((ROOT / "evidence/warehouse/manifest.json").read_text(encoding="utf-8"))
    database = Path(warehouse["database_path"])
    batch_size = int(os.environ.get("CONTEXTWEAVE_PILOT_BATCH_SIZE", "4"))
    if batch_size < 1 or batch_size > 16:
        raise ValueError("pilot batch size must be 1..16")
    remaining = [task for task in tasks if task["task_id"] not in existing]
    limit = int(os.environ.get("CONTEXTWEAVE_PILOT_LIMIT", "0"))
    if limit > 0:
        remaining = remaining[:limit]
    completed_rows = [existing[task_id] for task_id in task_ids if task_id in existing]
    for offset in range(0, len(remaining), batch_size):
        chunk = remaining[offset : offset + batch_size]
        prompts = []
        context_sizes = []
        for task in chunk:
            if method == "C1":
                context, context_tokens, _selected, _behavior = plan_context(
                    task["query"], rankings[task["task_id"]], docs, tokenizer
                )
            else:
                context, context_tokens = _context_for(
                    task["query"], docs, bm25, doc_token_costs, tokenizer
                )
            context_sizes.append(context_tokens)
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Schema context:\n{context}\n\nQuestion: {task['query']}",
                },
            ]
            prompts.append(
                tokenizer.apply_chat_template(
                    messages, tokenize=False, add_generation_prompt=True, enable_thinking=False
                )
            )
        encoded: Any = tokenizer(
            prompts, padding=True, return_tensors="pt", add_special_tokens=False
        )
        batch: Any = encoded.to("cuda")
        begin = time.perf_counter()
        with torch.inference_mode():
            outputs = model.generate(
                **batch,
                do_sample=False,
                max_new_tokens=160,
                pad_token_id=tokenizer.pad_token_id,
            )
        torch.cuda.synchronize()
        batch_latency = time.perf_counter() - begin
        for index, task in enumerate(chunk):
            generated = outputs[index][batch["input_ids"].shape[1] :]
            decoded = cast(str, tokenizer.decode(generated, skip_special_tokens=True))
            sql = _sql_from_text(decoded)
            status = "NO_SQL"
            result_hash = None
            if sql:
                try:
                    claims = Claims(
                        "pilot",
                        task["tenant_id"],
                        tuple(task["account_ids"]),
                        frozenset({"analytics:read"}),
                        "pilot",
                        0,
                        2**31,
                    )
                    result = run_readonly_sql(database, sql, claims, timeout_seconds=10)
                    result_hash = normalized_hash(result["columns"], result["rows"])
                    status = (
                        "CORRECT" if result_hash == task["gold_result_hash"] else "WRONG_RESULT"
                    )
                except SecurityError as exc:
                    status = f"EXECUTION_ERROR:{type(exc).__name__}"
            receipt = {
                "task_id": task["task_id"],
                "task_manifest_sha256": task_identity,
                "method": method,
                "context_budget_tokens": 1024,
                "context_tokens": context_sizes[index],
                "input_tokens": int(batch["attention_mask"][index].sum().item()),
                "output_tokens": int((generated != tokenizer.pad_token_id).sum().item()),
                "batch_latency_seconds": batch_latency,
                "batch_size": len(chunk),
                "sql": sql,
                "result_hash": result_hash,
                "status": status,
                "device": "cuda",
                "dtype": "bfloat16",
                "backend": "transformers",
                "model_revision": QWEN_REVISION,
            }
            completed_rows.append(receipt)
        _atomic_checkpoint(out, completed_rows)
        print(f"{method} checkpoint {len(completed_rows)}/{len(tasks)}", flush=True)
    outcomes = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines() if line]
    if len(outcomes) != len(tasks) or {x["task_id"] for x in outcomes} != set(task_ids):
        return {"status": "RUNNING", "completed": len(outcomes), "total": len(tasks)}
    summary = {
        "started_at_utc": started,
        "ended_at_utc": utc_now(),
        "task_count": len(tasks),
        "task_success_count": sum(x["status"] == "CORRECT" for x in outcomes),
        "task_success_rate": sum(x["status"] == "CORRECT" for x in outcomes) / len(outcomes),
        "load_seconds": load_seconds,
        "peak_vram_bytes": torch.cuda.max_memory_allocated(),
        "model_revision": QWEN_REVISION,
        "backend": "transformers",
        "dtype": "bfloat16",
        "device": torch.cuda.get_device_name(0),
        "batch_size": batch_size,
        "task_manifest_sha256": task_identity,
        "result_file_sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
        "evidence_class": "Q",
    }
    atomic_json(ROOT / f"evidence/pilot/{method.lower()}_summary.json", summary)
    record(
        "E06",
        f"E06-{method.lower()}-qwen-pilot",
        {
            "method": method,
            "budget": 1024,
            "max_new_tokens": 160,
            "do_sample": False,
            "batch_size": batch_size,
        },
        {"T3": warehouse["database_sha256"], "Qwen": QWEN_REVISION, "tasks": task_identity},
        {
            "device_backend": "CUDA/transformers",
            "device": summary["device"],
            "dtype": "bfloat16",
            "batch_size": batch_size,
            "peak_vram_bytes": summary["peak_vram_bytes"],
        },
        "PASS",
        [
            f"evidence/pilot/{method.lower()}_qwen3_4b.jsonl",
            f"evidence/pilot/{method.lower()}_summary.json",
        ],
        "Q",
        started,
    )
    return summary


if __name__ == "__main__":
    print(json.dumps(run_pilot(), indent=2))
