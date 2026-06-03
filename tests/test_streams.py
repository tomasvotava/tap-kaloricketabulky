from datetime import UTC, date, datetime
from typing import cast

from kaloricketabulky.sdk.models.snapshot import Snapshot
from tap_kaloricketabulky.client import PerDayStream
from tap_kaloricketabulky.tap import TapKaloricketabulky

from tests.conftest import FakeSyncClient

BASE_CONFIG = {
    "email": "e@x.cz",
    "password": "pw",
    "start_date": "2026-01-01T00:00:00Z",
    "request_delay_seconds": 0.0,
    "lookback_days": 3,
}


def _tap(**overrides: object) -> TapKaloricketabulky:
    return TapKaloricketabulky(config={**BASE_CONFIG, **overrides}, validate_config=False)


def _tap_with_fake(**overrides: object) -> TapKaloricketabulky:
    tap = _tap(**overrides)
    tap.__dict__["sync_client"] = FakeSyncClient()  # seam: pre-set the cached_property
    return tap


def test_window_first_run_starts_at_start_date() -> None:
    stream = cast(PerDayStream, _tap().streams["streak"])
    start, end = stream.window(None)
    assert start == date(2026, 1, 1)  # lookback clamped to start_date floor
    assert end == datetime.now(tz=UTC).date()


def test_window_respects_end_date() -> None:
    stream = cast(PerDayStream, _tap(end_date="2026-02-01T00:00:00Z").streams["streak"])
    _, end = stream.window(None)
    assert end == date(2026, 2, 1)


def test_diary_emits_one_record_per_day_with_injected_date() -> None:
    tap = _tap_with_fake(start_date="2026-03-01T00:00:00Z", end_date="2026-03-03T00:00:00Z", lookback_days=0)
    records = cast(list[dict[str, object]], list(tap.streams["diary"].get_records(None)))
    assert [r["date"] for r in records] == ["2026-03-01", "2026-03-02", "2026-03-03"]
    assert records[0]["energy_total"] == 101.0


def test_streak_record_shape() -> None:
    tap = _tap_with_fake(start_date="2026-03-01T00:00:00Z", end_date="2026-03-01T00:00:00Z", lookback_days=0)
    records = cast(list[dict[str, object]], list(tap.streams["streak"].get_records(None)))
    assert records == [{"date": "2026-03-01", "streak": 1}]


def test_weight_snapshot_is_full_table_over_complete_window() -> None:
    captured: dict[str, tuple[object, ...]] = {}

    class FakeSnap:
        def call(self, method: str, *args: object) -> object:
            assert method == "get_snapshot"
            captured["args"] = args  # (metric, start, end)
            return Snapshot.model_validate({"type": "weight", "unit": "kg", "min": 70.0, "max": 72.0})

    # lookback_days set high to prove FULL_TABLE ignores it and always starts at start_date.
    tap = _tap(start_date="2026-03-01T00:00:00Z", end_date="2026-03-05T00:00:00Z", lookback_days=99)
    tap.__dict__["sync_client"] = FakeSnap()
    stream = tap.streams["snapshot_weight"]
    assert stream.replication_method == "FULL_TABLE"
    records = cast(list[dict[str, object]], list(stream.get_records(None)))
    assert len(records) == 1
    assert records[0]["type"] == "weight"
    _metric, start, end = captured["args"]
    assert (start, end) == (date(2026, 3, 1), date(2026, 3, 5))


def test_optional_snapshot_emits_one_record_per_metric() -> None:
    class FakeOpt:
        def call(self, method: str, *args: object) -> object:
            assert method == "get_optional_snapshots"
            return [Snapshot.model_validate({"type": "Steps"}), Snapshot.model_validate({"type": "Mood"})]

    tap = _tap(start_date="2026-03-01T00:00:00Z", end_date="2026-03-05T00:00:00Z", lookback_days=0)
    tap.__dict__["sync_client"] = FakeOpt()
    records = cast(list[dict[str, object]], list(tap.streams["snapshot_optional"].get_records(None)))
    assert {r["type"] for r in records} == {"Steps", "Mood"}


def test_window_start_uses_literal_date_for_nonutc_offset() -> None:
    # +02:00 midnight must not roll back to the previous calendar day
    stream = cast(PerDayStream, _tap(start_date="2026-01-01T00:00:00+02:00").streams["streak"])
    start, _ = stream.window(None)
    assert start == date(2026, 1, 1)


def test_window_resumes_from_bookmark_minus_lookback() -> None:
    state = {"bookmarks": {"diary": {"replication_key": "date", "replication_key_value": "2026-03-10"}}}
    tap = TapKaloricketabulky(config=BASE_CONFIG, state=state, validate_config=False)
    stream = cast(PerDayStream, tap.streams["diary"])
    # Mirror what the SDK does at the start of each sync partition: promote
    # replication_key_value → starting_replication_value so the stream can read it.
    stream._write_starting_replication_value(None)
    start, _ = stream.window(None)
    assert start == date(2026, 3, 7)  # bookmark 2026-03-10 minus lookback_days=3
