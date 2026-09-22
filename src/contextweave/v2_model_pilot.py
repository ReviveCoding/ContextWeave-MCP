"""Resumable paired Qwen3-4B inference for the v2 qualification protocol."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, cast

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from contextweave.benchmark import normalized_hash
from contextweave.context_planner import plan_context
from contextweave.evidence import ROOT, atomic_json, load_state, save_state, utc_now
from contextweave.model_pilot import MODEL_DIR, QWEN_REVISION, _context_for, _sql_from_text
from contextweave.retrieval import BM25, corpus
from contextweave.security import Claims, SecurityError, run_readonly_sql

PROTOCOL = "ContextWeave-v2-family-diverse-qualification"
BEHAVIORS = ("CLARIFY", "REFRESH", "REFUSE", "RETRY", "ABSTAIN")
SYSTEM_PROMPT = (
    "You operate a governed analytical warehouse. Return exactly one safe DuckDB SELECT query when the request "
    "can be answered. When it cannot yet be executed safely, begin the response with exactly one behavior token: "
    "CLARIFY, REFRESH, REFUSE, RETRY, or ABSTAIN, followed by a short reason. Never output SQL after a behavior "
    "token. Use supplied schema and exact governed metric formulas. Never access files, extensions, or networks."
)


def _behavior_from_text(text: str) -> str | None:
    cleaned = text.strip().replace("```", "").strip().upper()
    return next((behavior for behavior in BEHAVIORS if re.match(rf"^{behavior}\b", cleaned)), None)


def _gpu_compute_pids() -> set[int]:
    result = subprocess.run(
        ["nvidia-smi", "--query-compute-apps=pid", "--format=csv,noheader"],
        text=True,
        capture_output=True,
        check=True,
    )
    return {int(line.strip()) for line in result.stdout.splitlines() if line.strip().isdigit()}


def _checkpoint(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as output:
        for row in rows:
            output.write(json.dumps(row, sort_keys=True) + "\n")
        output.flush()
        os.fsync(output.fileno())
        temporary = Path(output.name)
    os.replace(temporary, path)


def _progress(method: str, count: int, total: int, identity: str) -> None:
    state = load_state()
    active = state.get("active_long_running_process")
    if not isinstance(active, dict) or active.get("task_manifest_sha256") != identity:
        raise RuntimeError("v2 active GPU identity changed")
    active["completed_rows"] = count
    active["last_checkpoint_at_utc"] = utc_now()
    state["next_legal_action"] = (
        f"Finish v2 {method} on frozen qualification manifest {identity}; then complete paired v2 E07."
    )
    save_state(state)
    (ROOT / "NEXT_ACTION.md").write_text(
        f"# Next action\n\nV2 {method} CUDA qualification has {count}/{total} atomic checkpoint rows on `{identity}`. "
        "Resume the same method after any interruption. Complete paired B2/C1 and clustered E07 before any freeze.\n",
        encoding="utf-8",
    )


def run() -> dict[str, Any]:
    if _gpu_compute_pids():
        raise RuntimeError("GPU is not exclusively idle before v2 Qwen load")
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA required; no CPU fallback")
    task_path = ROOT / "benchmarks/v2_pilot_tasks.jsonl"
    manifest = json.loads((ROOT / "benchmarks/v2_pilot_manifest.json").read_text())
    identity = hashlib.sha256(task_path.read_bytes()).hexdigest()
    if identity != manifest["task_file_sha256"] or manifest["protocol_identity"] != PROTOCOL:
        raise RuntimeError("v2 task/protocol identity changed")
    tasks = [json.loads(line) for line in task_path.read_text().splitlines() if line]
    method = os.environ.get("CONTEXTWEAVE_V2_METHOD", "B2")
    if method not in {"B2", "C1"}:
        raise ValueError("CONTEXTWEAVE_V2_METHOD must be B2 or C1")
    out = ROOT / f"evidence/pilot_v2/{method.lower()}_qwen3_4b.jsonl"
    existing: dict[str, dict[str, Any]] = {}
    if out.exists():
        for line in out.read_text().splitlines():
            if line:
                row = json.loads(line)
                if row["task_manifest_sha256"] != identity or row["method"] != method:
                    raise RuntimeError("v2 checkpoint identity changed")
                if row["task_id"] in existing:
                    raise RuntimeError("duplicate v2 checkpoint row")
                existing[row["task_id"]] = row
    task_ids = [task["task_id"] for task in tasks]
    if len(tasks) != 360 or len(set(task_ids)) != 360 or not set(existing) <= set(task_ids):
        raise RuntimeError("v2 task/checkpoint IDs invalid")
    docs = corpus()
    bm25 = BM25([doc["text"] for doc in docs])
    rankings: dict[str, list[str]] = {}
    if method == "C1":
        ranking_path = ROOT / "evidence/retrieval_v2/rankings.jsonl"
        receipt = json.loads((ROOT / "evidence/retrieval_v2/rankings_receipt.json").read_text())
        if hashlib.sha256(ranking_path.read_bytes()).hexdigest() != receipt["rankings_sha256"]:
            raise RuntimeError("v2 ranking identity changed")
        rankings = {
            row["task_id"]: row["reranked"]
            for row in (json.loads(line) for line in ranking_path.read_text().splitlines() if line)
        }
        if set(rankings) != set(task_ids):
            raise RuntimeError("v2 ranking task IDs changed")
    started = utc_now()
    tokenizer = AutoTokenizer.from_pretrained(str(MODEL_DIR), local_files_only=True)
    tokenizer.padding_side = "left"
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    doc_token_costs = [len(tokenizer.encode(doc["text"], add_special_tokens=False)) for doc in docs]
    torch.cuda.reset_peak_memory_stats()
    load_start = time.perf_counter()
    model: Any = AutoModelForCausalLM.from_pretrained(
        str(MODEL_DIR), dtype=torch.bfloat16, device_map="cuda", local_files_only=True
    )
    model.eval()
    torch.cuda.synchronize()
    owner_pids = _gpu_compute_pids()
    if len(owner_pids) != 1:
        raise RuntimeError(f"expected one v2 GPU owner, observed {sorted(owner_pids)}")
    load_seconds = time.perf_counter() - load_start
    database = Path(
        json.loads((ROOT / "evidence/warehouse/manifest.json").read_text())["database_path"]
    )
    batch_size = int(os.environ.get("CONTEXTWEAVE_V2_BATCH_SIZE", "4"))
    if batch_size != 4:
        raise RuntimeError("v2 frozen qualification batch size is 4")
    completed = [existing[task_id] for task_id in task_ids if task_id in existing]
    remaining = [task for task in tasks if task["task_id"] not in existing]
    for offset in range(0, len(remaining), batch_size):
        if _gpu_compute_pids() != owner_pids:
            raise RuntimeError("v2 GPU ownership changed")
        chunk = remaining[offset : offset + batch_size]
        prompts: list[str] = []
        context_sizes: list[int] = []
        for task in chunk:
            if method == "C1":
                context, context_tokens, _, _ = plan_context(
                    task["query"], rankings[task["task_id"]], docs, tokenizer
                )
            else:
                context, context_tokens = _context_for(
                    task["query"], docs, bm25, doc_token_costs, tokenizer
                )
            context_sizes.append(context_tokens)
            scenario = f"\nRuntime facts: {task['scenario']}" if task.get("scenario") else ""
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Schema and governed context:\n{context}{scenario}\n\nQuestion: {task['query']}",
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
        latency = time.perf_counter() - begin
        for index, task in enumerate(chunk):
            generated = outputs[index][batch["input_ids"].shape[1] :]
            decoded = cast(str, tokenizer.decode(generated, skip_special_tokens=True))
            sql = _sql_from_text(decoded)
            behavior = _behavior_from_text(decoded)
            result_hash = None
            if task["expected_behavior"] == "ANSWER":
                status = "NO_SQL"
                if sql:
                    try:
                        claims = Claims(
                            "v2_pilot",
                            task["tenant_id"],
                            tuple(task["account_ids"]),
                            frozenset({"analytics:read"}),
                            "v2",
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
            else:
                status = (
                    "CORRECT"
                    if behavior == task["expected_behavior"] and sql is None
                    else "WRONG_BEHAVIOR"
                )
            completed.append(
                {
                    "task_id": task["task_id"],
                    "semantic_family": task["semantic_family"],
                    "expected_behavior": task["expected_behavior"],
                    "observed_behavior": behavior,
                    "task_manifest_sha256": identity,
                    "protocol_identity": PROTOCOL,
                    "method": method,
                    "context_budget_tokens": 1024,
                    "context_tokens": context_sizes[index],
                    "input_tokens": int(batch["attention_mask"][index].sum().item()),
                    "output_tokens": int((generated != tokenizer.pad_token_id).sum().item()),
                    "batch_latency_seconds": latency,
                    "batch_size": len(chunk),
                    "sql": sql,
                    "result_hash": result_hash,
                    "status": status,
                    "device": "cuda",
                    "dtype": "bfloat16",
                    "backend": "transformers",
                    "model_revision": QWEN_REVISION,
                }
            )
        _checkpoint(out, completed)
        print(f"v2 {method} checkpoint {len(completed)}/{len(tasks)}", flush=True)
        if len(completed) % 24 == 0 or len(completed) == len(tasks):
            _progress(method, len(completed), len(tasks), identity)
    outcomes = [json.loads(line) for line in out.read_text().splitlines() if line]
    summary = {
        "protocol_identity": PROTOCOL,
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
        "task_manifest_sha256": identity,
        "result_file_sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
        "evidence_class": "Q",
    }
    atomic_json(ROOT / f"evidence/pilot_v2/{method.lower()}_summary.json", summary)
    return summary


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
