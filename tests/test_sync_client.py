from datetime import date

from tap_kaloricketabulky.client import SyncClient

from tests.conftest import FakeKaloricClient

CONFIG = {"email": "e@x.cz", "password": "pw", "request_delay_seconds": 0.0}


def test_logs_in_lazily_once() -> None:
    fake = FakeKaloricClient()
    client = SyncClient(CONFIG, kaloric_client=fake)
    assert fake.logins == []
    client.call("get_streak", date(2026, 6, 1))
    client.call("get_streak", date(2026, 6, 2))
    assert fake.logins == [("e@x.cz", "pw")]
    client.close()


def test_relogins_once_on_auth_error() -> None:
    fake = FakeKaloricClient(fail_auth_times=1)
    client = SyncClient(CONFIG, kaloric_client=fake)
    result = client.call("get_streak", date(2026, 6, 1))
    assert result == 7
    assert len(fake.logins) == 2  # initial + re-login
    client.close()
