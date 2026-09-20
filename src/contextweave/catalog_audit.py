"""E05 governed catalog and dependency graph audit."""

from __future__ import annotations

import dataclasses
import json
from typing import Any

from contextweave.catalog import METRICS, metric_graph
from contextweave.evidence import ROOT, atomic_json, record, utc_now


def audit_catalog() -> dict[str, Any]:
    started = utc_now()
    warehouse = json.loads((ROOT / "evidence/warehouse/manifest.json").read_text(encoding="utf-8"))
    graph = metric_graph()
    for metric in METRICS:
        closure = graph.closure({metric.metric_id})
        for table in metric.required_tables:
            if f"TABLE:{table}" not in closure:
                raise AssertionError(f"missing table dependency: {metric.metric_id} {table}")
        for column in metric.required_columns:
            if f"COLUMN:{column}" not in closure:
                raise AssertionError(f"missing column dependency: {metric.metric_id} {column}")
    catalog = [dataclasses.asdict(metric) for metric in METRICS]
    graph_data = {
        "nodes": [dataclasses.asdict(node) for node in graph.nodes.values()],
        "edges": [dataclasses.asdict(edge) for edges in graph.outgoing.values() for edge in edges],
    }
    atomic_json(ROOT / "warehouse/metric_catalog.json", catalog)
    atomic_json(ROOT / "warehouse/dependency_graph.json", graph_data)
    audit = {
        "metric_count": len(catalog),
        "node_count": len(graph.nodes),
        "edge_count": len(graph_data["edges"]),
        "warehouse_sha256": warehouse["database_sha256"],
        "critical_closure_audited": True,
    }
    atomic_json(ROOT / "evidence/catalog/audit.json", audit)
    record(
        "E05",
        "E05-catalog-graph-v2",
        {"catalog_version": "v1"},
        {"T3": warehouse["database_sha256"]},
        {"device_backend": "CPU"},
        "PASS",
        [
            "warehouse/metric_catalog.json",
            "warehouse/dependency_graph.json",
            "evidence/catalog/audit.json",
        ],
        "D",
        started,
    )
    return audit
