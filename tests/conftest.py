from __future__ import annotations

from datetime import date

from kaloricketabulky.sdk.errors import AuthError
from kaloricketabulky.sdk.models.diary import Diary


class FakeKaloricClient:
    """Stand-in for the async SDK client; records calls, can fail auth once."""

    def __init__(self, *, fail_auth_times: int = 0) -> None:
        self.logins: list[tuple[str, str]] = []
        self.calls: list[tuple[str, date]] = []
        self._fail_auth_times = fail_auth_times

    async def login(self, email: str, password: str) -> None:
        self.logins.append((email, password))

    async def get_streak(self, day: date) -> int:
        self.calls.append(("get_streak", day))
        if self._fail_auth_times > 0:
            self._fail_auth_times -= 1
            raise AuthError("session expired")
        return 7

    async def aclose(self) -> None:
        pass


class FakeSyncClient:
    """Infra-boundary fake for stream tests: returns SDK models without network."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, date]] = []

    def call(self, method: str, day: date) -> object:
        self.calls.append((method, day))
        if method == "get_diary":
            return Diary.model_validate({"date": 1_700_000_000_000, "energyTotal": 100.0 + day.day})
        if method == "get_streak":
            return day.day
        raise AssertionError(method)
