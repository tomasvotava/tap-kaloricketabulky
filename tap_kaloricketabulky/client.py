"""Synchronous bridge over the async kaloricketabulky-sdk client.

Singer SDK streams are sync generators; the SDK client is async. SyncClient owns one event
loop and one async client for the whole tap run, logs in lazily, re-logs-in once on AuthError,
and throttles requests to stay a respectful guest.
"""

from __future__ import annotations

import asyncio
import atexit
import time
from pathlib import Path
from typing import Any

import httpx
from kaloricketabulky.sdk import KaloricketabulkyClient
from kaloricketabulky.sdk.errors import AuthError

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
