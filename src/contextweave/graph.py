"""Typed schema dependency graph with deterministic critical closure."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

NODE_TYPES = frozenset({"TABLE", "COLUMN", "METRIC", "ENTITY", "POLICY", "DOCUMENT"})
EDGE_TYPES = frozenset(
    {
        "foreign_key",
        "contains",
        "metric_requires",
        "derived_from",
        "synonym_of",
        "documented_by",
        "governed_by",
        "freshness_depends_on",
    }
)
CRITICAL = frozenset({"metric_requires", "foreign_key", "governed_by", "freshness_depends_on"})


@dataclass(frozen=True, order=True)
class Node:
    id: str
    kind: str
    text: str
    token_cost: int
    tenant_id: str | None = None
    sensitivity: str = "public"
    version: str = "v1"

    def __post_init__(self) -> None:
        if self.kind not in NODE_TYPES or self.token_cost < 0:
            raise ValueError("invalid graph node")


@dataclass(frozen=True, order=True)
class Edge:
    source: str
    target: str
    kind: str

    def __post_init__(self) -> None:
        if self.kind not in EDGE_TYPES:
            raise ValueError("invalid graph edge")


class DependencyGraph:
    def __init__(self, nodes: list[Node], edges: list[Edge]) -> None:
        self.nodes = {node.id: node for node in nodes}
        if len(self.nodes) != len(nodes):
            raise ValueError("duplicate node ID")
        self.outgoing: dict[str, list[Edge]] = {key: [] for key in self.nodes}
        for edge in edges:
            if edge.source not in self.nodes or edge.target not in self.nodes:
                raise ValueError(f"dangling graph edge: {edge}")
            self.outgoing[edge.source].append(edge)
        for adjacency in self.outgoing.values():
            adjacency.sort()

    def closure(self, selected: set[str], edge_types: frozenset[str] = CRITICAL) -> set[str]:
        missing = selected - self.nodes.keys()
        if missing:
            raise KeyError(f"unknown nodes: {sorted(missing)}")
        seen = set(selected)
        queue = deque(sorted(selected))
        while queue:
            for edge in self.outgoing[queue.popleft()]:
                if edge.kind in edge_types and edge.target not in seen:
                    seen.add(edge.target)
                    queue.append(edge.target)
        return seen

    def ordered_closure(self, selected: set[str]) -> list[Node]:
        return [self.nodes[key] for key in sorted(self.closure(selected))]
