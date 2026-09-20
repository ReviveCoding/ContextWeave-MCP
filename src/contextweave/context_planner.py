"""Development C1 context planner using ranked candidates and exact metric closure."""

from __future__ import annotations

import re
from typing import Any

from contextweave.catalog import METRICS, metric_graph


def inferred_metric_ids(query: str) -> set[str]:
    lowered = query.casefold()
    found = set()
    for metric in METRICS:
        names = (metric.canonical_name, *metric.aliases)
        if any(re.search(r"\b" + re.escape(name.casefold()) + r"\b", lowered) for name in names):
            found.add(metric.metric_id)
    if "cost per attributed conversion" in lowered:
        found.add("M_CPA")
    return found


def plan_context(
    query: str,
    ranking: list[str],
    docs: list[dict[str, Any]],
    tokenizer: Any,
    budget: int = 1024,
) -> tuple[str, int, tuple[str, ...], str]:
    if budget < 1:
        return "", 0, (), "ABSTAIN"
    lookup = {doc["id"]: doc["text"] for doc in docs}
    graph = metric_graph()
    required = graph.closure(inferred_metric_ids(query))
    if not required <= lookup.keys():
        return "", 0, (), "ABSTAIN"
    # The exact governed metric dependencies are placed before optional ranking hits.
    ordered = [key for key in sorted(required) if key in lookup]
    for key in ranking:
        if key not in ordered and key in lookup:
            ordered.append(key)
    selected: list[str] = []
    for key in ordered:
        candidate = "\n".join([*(lookup[item] for item in selected), lookup[key]])
        token_count = len(tokenizer.encode(candidate, add_special_tokens=False))
        if token_count <= budget:
            selected.append(key)
        elif key in required:
            return "", 0, (), "ABSTAIN"
    context = "\n".join(lookup[key] for key in selected)
    return (
        context,
        len(tokenizer.encode(context, add_special_tokens=False)),
        tuple(selected),
        "ANSWER",
    )
