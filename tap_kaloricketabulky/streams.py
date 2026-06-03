"""Concrete streams for tap-kaloricketabulky."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from typing import ClassVar

from kaloricketabulky.sdk.models.snapshot import SnapshotType

from tap_kaloricketabulky.client import SCHEMAS_DIR, PerDayStream, RangeSnapshotStream


class DiaryStream(PerDayStream):
    name = "diary"
    sdk_method = "get_diary"
    primary_keys = ("date",)
    schema_filepath = SCHEMAS_DIR / "diary.json"


class DiarySummaryStream(PerDayStream):
    name = "diary_summary"
    sdk_method = "get_diary_summary"
    primary_keys = ("date",)
    schema_filepath = SCHEMAS_DIR / "diary_summary.json"


class StatisticsSummaryStream(PerDayStream):
    name = "statistics_summary"
    sdk_method = "get_statistics_summary"
    primary_keys = ("date",)
    schema_filepath = SCHEMAS_DIR / "statistics_summary.json"


class StreakStream(PerDayStream):
    """Streak returns a bare int; no Pydantic model, so the schema is inline and `fetch`
    wraps the int in a record body (PerDayStream injects the `date`)."""

    name = "streak"
    primary_keys = ("date",)
    schema: ClassVar[dict[str, object]] = {
        "type": "object",
        "additionalProperties": True,
        "properties": {
            "date": {"type": ["string", "null"], "format": "date"},
            "streak": {"type": ["integer", "null"]},
        },
    }

    def fetch(self, day: date) -> Mapping[str, object]:
        return {"streak": self.client.call("get_streak", day)}


class _SnapshotStream(RangeSnapshotStream):
    primary_keys = ("type",)  # one record per run; `type` is the metric name
    schema_filepath = SCHEMAS_DIR / "snapshot.json"


class SnapshotEnergyStream(_SnapshotStream):
    name = "snapshot_energy"
    sdk_method = "get_snapshot"
    metric = SnapshotType.ENERGY


class SnapshotNutrientsStream(_SnapshotStream):
    name = "snapshot_nutrients"
    sdk_method = "get_snapshot"
    metric = SnapshotType.NUTRIENTS


class SnapshotDrinkStream(_SnapshotStream):
    name = "snapshot_drink"
    sdk_method = "get_snapshot"
    metric = SnapshotType.DRINK


class SnapshotWeightStream(_SnapshotStream):
    name = "snapshot_weight"
    sdk_method = "get_snapshot"
    metric = SnapshotType.WEIGHT


class SnapshotOptionalStream(_SnapshotStream):
    name = "snapshot_optional"
    sdk_method = "get_optional_snapshots"
    metric = None
    primary_keys = ("guid",)  # one record per custom metric; guid is its stable id
