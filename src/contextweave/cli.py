"""Restartable stage entry points. Unimplemented stages never receive PASS receipts."""

from __future__ import annotations

import argparse
import json
from typing import Any

from contextweave.evidence import ROOT, load_state, record, utc_now


def desktop() -> dict[str, Any]:
    started = utc_now()
    registry = json.loads((ROOT / "sources/registry.json").read_text(encoding="utf-8"))
    if len(registry["sources"]) < 3:
        raise ValueError("source registry incomplete")
    record(
        "E00",
        "E00-desktop-study",
        {"source_count": len(registry["sources"])},
        {},
        {"device_backend": "CPU", "source_review": "official upstream pages"},
        "PASS",
        ["reports/DESKTOP_STUDY.md", "sources/registry.json", "NEXT_ACTION.md"],
        "Q",
        started,
    )
    return {"status": "PASS", "source_count": len(registry["sources"])}


def run_one(stage: str) -> dict[str, Any]:
    if stage == "E00":
        return desktop()
    if stage == "E01":
        from contextweave.qualify import qualify

        return qualify()
    if stage == "E02":
        from contextweave.data import source_validation

        return source_validation()
    if stage == "E03":
        from contextweave.data import eda

        return eda()
    if stage == "E04":
        from contextweave.warehouse import build_warehouse

        return build_warehouse()
    if stage == "E05":
        from contextweave.catalog_audit import audit_catalog

        return audit_catalog()
    raise NotImplementedError(f"{stage} has not been implemented or executed")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action",
        choices=(
            "desktop",
            "qualify",
            "acquire",
            "eda",
            "warehouse",
            "catalog",
            "run-all",
            "resume",
            "state",
        ),
    )
    args = parser.parse_args()
    if args.action == "state":
        print(json.dumps(load_state(), indent=2))
        return
    mapping = {
        "desktop": "E00",
        "qualify": "E01",
        "acquire": "E02",
        "eda": "E03",
        "warehouse": "E04",
        "catalog": "E05",
    }
    if args.action in mapping:
        print(json.dumps(run_one(mapping[args.action]), indent=2))
        return
    for stage in ("E00", "E01", "E02", "E03", "E04", "E05"):
        if stage not in load_state()["completed_stages"]:
            print(json.dumps(run_one(stage), indent=2))
    raise NotImplementedError(
        "E06–E26 require implementation and evidence; no false completion recorded"
    )


if __name__ == "__main__":
    main()
