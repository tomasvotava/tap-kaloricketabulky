"""Regenerate Singer JSON schemas from the kaloricketabulky-sdk Pydantic models.

Run: uv run python scripts/gen_schemas.py
Never hand-edit tap_kaloricketabulky/schemas/*.json — change the SDK models and rerun.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

from kaloricketabulky.sdk.models.diary import Diary
from kaloricketabulky.sdk.models.snapshot import Snapshot
from kaloricketabulky.sdk.models.summary import DiarySummary, StatisticsSummary
from pydantic import BaseModel

# A date-typed nullable property used for the standardised replication keys the tap injects.
DATE_PROP: dict[str, Any] = {"type": ["string", "null"], "format": "date"}

# stream file -> (model, {property name: forced schema}). Forced props standardise the `date`
# replication key the per-day streams inject. Snapshot streams are FULL_TABLE and inject
# nothing, so the Snapshot schema is dumped faithfully (no forced overrides).
MODELS: dict[str, tuple[type[BaseModel], dict[str, dict[str, Any]]]] = {
    "diary": (Diary, {"date": DATE_PROP}),
    "diary_summary": (DiarySummary, {"date": DATE_PROP}),
    "statistics_summary": (StatisticsSummary, {"date": DATE_PROP}),
    "snapshot": (Snapshot, {}),
}


def _inline_refs(node: Any, defs: dict[str, Any]) -> Any:
    """Resolve every {"$ref": "#/$defs/X"} into the referenced subschema (models are acyclic)."""
    if isinstance(node, dict):
        if "$ref" in node:
            name = node["$ref"].rsplit("/", 1)[-1]
            return _inline_refs(defs[name], defs)
        return {k: _inline_refs(v, defs) for k, v in node.items() if k != "$defs"}
    if isinstance(node, list):
        return [_inline_refs(v, defs) for v in node]
    return node


def _normalise_nullable(node: Any) -> Any:
    """Collapse Pydantic's anyOf:[X, {"type":"null"}] into Singer's "type":[..., "null"] idiom."""
    if isinstance(node, dict):
        node = {k: _normalise_nullable(v) for k, v in node.items()}
        any_of = node.get("anyOf")
        if isinstance(any_of, list) and len(any_of) == 2 and {"type": "null"} in any_of:
            other = next(b for b in any_of if b != {"type": "null"})
            if isinstance(other.get("type"), str):
                merged = {k: v for k, v in node.items() if k != "anyOf"}
                merged.update({k: v for k, v in other.items() if k != "type"})
                merged["type"] = [other["type"], "null"]
                return merged
        return node
    if isinstance(node, list):
        return [_normalise_nullable(v) for v in node]
    return node


def _set_open(node: Any) -> Any:
    """Set additionalProperties: true on every object node (forgiving; mirrors extra='ignore')."""
    if isinstance(node, dict):
        node = {k: _set_open(v) for k, v in node.items()}
        if node.get("type") == "object" or "properties" in node:
            node["additionalProperties"] = True
        return node
    if isinstance(node, list):
        return [_set_open(v) for v in node]
    return node


def build_schema(model: type[BaseModel], forced: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Build a Singer-compatible JSON schema from a Pydantic model."""
    raw = model.model_json_schema(by_alias=False, mode="serialization")
    defs = raw.get("$defs", {})
    schema = cast(dict[str, Any], _inline_refs(raw, defs))
    schema = cast(dict[str, Any], _normalise_nullable(schema))
    schema = cast(dict[str, Any], _set_open(schema))
    schema.pop("title", None)
    schema.setdefault("properties", {})
    for prop, prop_schema in forced.items():
        schema["properties"][prop] = prop_schema
    return schema


def main() -> None:
    """Entry point: parse --out argument and write one JSON file per stream."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out",
        default=str(Path(__file__).resolve().parent.parent / "tap_kaloricketabulky" / "schemas"),
    )
    out = Path(parser.parse_args().out)
    out.mkdir(parents=True, exist_ok=True)
    for name, (model, forced) in MODELS.items():
        schema = build_schema(model, forced)
        (out / f"{name}.json").write_text(json.dumps(schema, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
