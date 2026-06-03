from datetime import UTC, date, datetime
from typing import cast

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
