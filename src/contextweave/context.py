"""Authorization-first context selection with fail-closed dependency budgeting."""

from __future__ import annotations

import re
from dataclasses import dataclass

from contextweave.graph import DependencyGraph, Node


@dataclass(frozen=True)
class ContextResult:
    behavior: str
    selected_ids: tuple[str, ...]
    context: str
    token_cost: int
    reason: str | None = None


def lexical_score(query: str, text: str) -> float:
    terms = set(re.findall(r"[\w]+", query.casefold()))
    words = set(re.findall(r"[\w]+", text.casefold()))
    return float(len(terms & words)) / max(len(terms), 1)


def select_context(
    query: str,
    graph: DependencyGraph,
    budget: int,
    tenant_id: str,
    authorized_ids: set[str],
    fresh_ids: set[str],
    required_ids: set[str],
) -> ContextResult:
    if budget < 0:
        raise ValueError("negative context budget")
    eligible = {
        key: node
        for key, node in graph.nodes.items()
        if key in authorized_ids and key in fresh_ids and (node.tenant_id in (None, tenant_id))
    }
    if not required_ids <= eligible.keys():
        return ContextResult(
            "REFRESH" if required_ids <= authorized_ids else "REFUSE",
            (),
            "",
            0,
            "required context unavailable",
        )
    closure = graph.closure(required_ids)
    if not closure <= eligible.keys():
        missing = closure - eligible.keys()
        return ContextResult(
            "REFRESH" if missing <= authorized_ids else "REFUSE",
            (),
            "",
            0,
            "critical dependency unavailable",
        )
    selected = set(closure)
    cost = sum(eligible[key].token_cost for key in selected)
    if cost > budget:
        return ContextResult("ABSTAIN", (), "", 0, "critical dependencies exceed budget")
    candidates: list[tuple[float, str, Node]] = []
    for key, node in eligible.items():
        if key not in selected:
            candidates.append((lexical_score(query, node.text), key, node))
    for _, key, node in sorted(candidates, key=lambda item: (-item[0], item[1])):
        if cost + node.token_cost <= budget:
            selected.add(key)
            cost += node.token_cost
    ordered = tuple(sorted(selected))
    return ContextResult("ANSWER", ordered, "\n".join(eligible[key].text for key in ordered), cost)
