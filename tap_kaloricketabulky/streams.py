"""Concrete streams for tap-kaloricketabulky."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from typing import ClassVar

from tap_kaloricketabulky.client import SCHEMAS_DIR, PerDayStream


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
