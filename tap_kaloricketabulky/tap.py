"""tap-kaloricketabulky: Singer tap for kaloricketabulky.cz."""

from __future__ import annotations

from functools import cached_property

from singer_sdk import Stream, Tap
from singer_sdk import typing as th

from tap_kaloricketabulky.client import SyncClient
from tap_kaloricketabulky.streams import (
    DiaryStream,
    DiarySummaryStream,
    SnapshotDrinkStream,
    SnapshotEnergyStream,
    SnapshotNutrientsStream,
    SnapshotOptionalStream,
    SnapshotWeightStream,
    StatisticsSummaryStream,
    StreakStream,
)

STREAM_TYPES: list[type[Stream]] = [
    DiaryStream,
    DiarySummaryStream,
    StatisticsSummaryStream,
    StreakStream,
    SnapshotEnergyStream,
    SnapshotNutrientsStream,
    SnapshotDrinkStream,
    SnapshotWeightStream,
    SnapshotOptionalStream,
]


class TapKaloricketabulky(Tap):
    """Extract diary, daily summaries, and long-term snapshots from kaloricketabulky.cz."""

    name = "tap-kaloricketabulky"

    config_jsonschema = th.PropertiesList(
        th.Property("email", th.StringType, required=True, secret=True, title="Login email"),
        th.Property("password", th.StringType, required=True, secret=True, title="Login password"),
        th.Property("start_date", th.DateTimeType, required=True, title="Earliest day to extract"),
        th.Property("end_date", th.DateTimeType, title="Latest day to extract (default: today)"),
        th.Property("lookback_days", th.IntegerType, default=3, title="Days to re-pull before the bookmark"),
        th.Property("request_delay_seconds", th.NumberType, default=0.5, title="Delay between API requests"),
        th.Property("base_url", th.StringType, title="API base URL"),
        th.Property("user_agent", th.StringType, title="User-Agent header"),
    ).to_dict()

    @cached_property
    def sync_client(self) -> SyncClient:
        return SyncClient(dict(self.config))

    def discover_streams(self) -> list[Stream]:
        return [stream_type(self) for stream_type in STREAM_TYPES]


if __name__ == "__main__":
    TapKaloricketabulky.cli()
