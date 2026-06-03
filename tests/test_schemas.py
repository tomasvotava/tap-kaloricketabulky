"""Tests for generated Singer JSON schemas."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from jsonschema import Draft7Validator, validate
from kaloricketabulky.sdk.models.diary import Diary

ROOT = Path(__file__).resolve().parent.parent
SCHEMAS_DIR = ROOT / "tap_kaloricketabulky" / "schemas"
GEN = ROOT / "scripts" / "gen_schemas.py"

GENERATED_FILES = ["diary.json", "diary_summary.json", "statistics_summary.json", "snapshot.json"]


def test_generated_schemas_are_valid_json_schema() -> None:
    for name in GENERATED_FILES:
        schema = json.loads((SCHEMAS_DIR / name).read_text())
        Draft7Validator.check_schema(schema)


def test_schemas_have_no_unresolved_refs_and_are_open() -> None:
    for name in GENERATED_FILES:
        text = (SCHEMAS_DIR / name).read_text()
        assert "$ref" not in text, f"{name} contains an unresolved $ref"
        assert "$defs" not in text, f"{name} contains leftover $defs"
        schema = json.loads(text)
        assert schema["additionalProperties"] is True


def test_committed_schemas_match_regeneration(tmp_path: Path) -> None:
    out = tmp_path / "schemas"
    subprocess.run([sys.executable, str(GEN), "--out", str(out)], check=True)  # noqa: S603
    for name in GENERATED_FILES:
        assert json.loads((out / name).read_text()) == json.loads((SCHEMAS_DIR / name).read_text()), (
            f"{name} is stale; run `uv run python scripts/gen_schemas.py`"
        )


def test_model_dump_validates_against_generated_schema() -> None:
    diary = Diary.model_validate(
        {
            "date": 1_700_000_000_000,
            "energyTotal": 1234.5,
            "times": [{"id": "m1", "title": "Snidane", "foodstuff": [{"id": "f1", "type": "food", "energy": "10,5"}]}],
        }
    )
    record = diary.model_dump(mode="json", by_alias=False) | {"date": "2023-11-14"}
    schema = json.loads((SCHEMAS_DIR / "diary.json").read_text())
    validate(record, schema)
