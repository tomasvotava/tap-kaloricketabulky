"""Synchronous bridge over the async kaloricketabulky-sdk client.

Singer SDK streams are sync generators; the SDK client is async. SyncClient owns one event
loop and one async client for the whole tap run, logs in lazily, re-logs-in once on AuthError,
and throttles requests to stay a respectful guest.
"""

from __future__ import annotations

import asyncio
import atexit
import time
from collections.abc import Iterable, Mapping
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import httpx
from kaloricketabulky.sdk import KaloricketabulkyClient
from kaloricketabulky.sdk.errors import AuthError
from singer_sdk import Stream
from singer_sdk.helpers.types import Context

SCHEMAS_DIR = Path(__file__).resolve().parent / "schemas"

DEFAULT_BASE_URL = "https://www.kaloricketabulky.cz"
DEFAULT_TIMEOUT = 30.0


class SyncClient:
    """Drives the async SDK client from synchronous stream code."""

    def __init__(self, config: dict[str, Any], *, kaloric_client: Any | None = None) -> None:
        self._email = config["email"]
        self._password = config["password"]
        self._delay = float(config.get("request_delay_seconds", 0.5))
        self._loop = asyncio.new_event_loop()
        self._http: httpx.AsyncClient | None = None
        if kaloric_client is not None:
            self._client = kaloric_client
        else:
            headers = {"User-Agent": config["user_agent"]} if config.get("user_agent") else None
            self._http = httpx.AsyncClient(
                base_url=config.get("base_url", DEFAULT_BASE_URL), timeout=DEFAULT_TIMEOUT, headers=headers
            )
            self._client = KaloricketabulkyClient(client=self._http)
        self._logged_in = False
        atexit.register(self.close)

    def _run(self, coro: Any) -> Any:
        return self._loop.run_until_complete(coro)

    def _ensure_login(self) -> None:
        if not self._logged_in:
            self._run(self._client.login(self._email, self._password))
            self._logged_in = True

    def call(self, method: str, *args: Any) -> Any:
        """Invoke an async SDK method by name, handling login, throttle, and one re-login retry."""
        self._ensure_login()
        if self._delay:
            time.sleep(self._delay)
        try:
            return self._run(getattr(self._client, method)(*args))
        except AuthError:
            self._logged_in = False
            self._ensure_login()
            return self._run(getattr(self._client, method)(*args))

    def close(self) -> None:
        if self._loop.is_closed():
            return
        try:
            if self._http is not None:
                self._run(self._http.aclose())
        finally:
            self._loop.close()


def _to_date(value: str) -> date:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).date()


class _KaloricStream(Stream):
    """Shared access to the SyncClient and the configured date window edges."""

    @property
    def client(self) -> SyncClient:
        return cast(SyncClient, self._tap.sync_client)  # type: ignore[attr-defined]

    @property
    def _start_floor(self) -> datetime:
        return datetime.fromisoformat(self.config["start_date"].replace("Z", "+00:00")).astimezone(UTC)

    def _end_date(self) -> date:
        end_cfg = self.config.get("end_date")
        return _to_date(end_cfg) if end_cfg else datetime.now(tz=UTC).date()


class RangeSnapshotStream(_KaloricStream):
    """FULL_TABLE: emit the complete current series for a metric each run.

    The endpoint returns the entire [from, to] series in ONE request, so incremental windowing
    would save zero requests while risking data loss: two runs sharing a window end but
    different starts collide on the primary key, and an upsert target would overwrite the
    broader window with the narrower one. FULL_TABLE always pulls [start_date, end] and emits
    the faithful Snapshot. Late edits to past days are picked up automatically (lookback is moot).
    `replication_key` is None, so the SDK reports replication_method == FULL_TABLE.
    """

    sdk_method: str
    metric: object | None = None  # SnapshotType member, or None for the optional list

    def _fetch(self, start: date, end: date) -> Iterable[object]:
        if self.metric is None:
            return cast(Iterable[object], self.client.call(self.sdk_method, start, end))
        return [self.client.call(self.sdk_method, self.metric, start, end)]

    def get_records(self, context: Context | None) -> Iterable[dict[str, object]]:
        start, end = self._start_floor.date(), self._end_date()
        for snap in self._fetch(start, end):
            yield cast(dict[str, object], cast(Any, snap).model_dump(mode="json", by_alias=False))


class PerDayStream(_KaloricStream):
    """INCREMENTAL: one record per calendar day; injects the queried day as `date`."""

    replication_key = "date"
    # Lookback re-emits days below the prior bookmark; the window's bounded end ensures the
    # SDK still records the true max key as the new bookmark after each run.
    is_sorted = False
    sdk_method: str

    def window(self, context: Context | None) -> tuple[date, date]:
        floor = self._start_floor.date()
        raw = self.get_starting_replication_key_value(context)
        if raw is None:  # first run: no prior bookmark
            return floor, self._end_date()
        lookback = timedelta(days=int(self.config.get("lookback_days", 3)))
        return max(_to_date(str(raw)) - lookback, floor), self._end_date()

    def fetch(self, day: date) -> Mapping[str, object]:
        """Return the record body for one day (without the injected `date`). Override per stream."""
        result: Any = self.client.call(self.sdk_method, day)
        return cast(Mapping[str, object], result.model_dump(mode="json", by_alias=False))

    def get_records(self, context: Context | None) -> Iterable[dict[str, object]]:
        start, end = self.window(context)
        day = start
        while day <= end:
            yield {**self.fetch(day), "date": day.isoformat()}
            day += timedelta(days=1)
