from tap_kaloricketabulky.tap import TapKaloricketabulky

CONFIG = {"email": "e@x.cz", "password": "pw", "start_date": "2026-01-01T00:00:00Z"}

PER_DAY_STREAMS = {"diary", "diary_summary", "statistics_summary", "streak"}


def test_discovers_per_day_streams() -> None:
    tap = TapKaloricketabulky(config=CONFIG, validate_config=False)
    discovered = {s.name for s in tap.discover_streams()}
    assert discovered >= PER_DAY_STREAMS


def test_config_schema_declares_secret_password_and_float_delay() -> None:
    props = TapKaloricketabulky.config_jsonschema["properties"]
    assert props["password"].get("secret") is True
    assert props["request_delay_seconds"]["type"] in ("number", ["number", "null"])


def test_about_lists_core_capabilities() -> None:
    caps = {c.value for c in TapKaloricketabulky.capabilities}
    assert {"catalog", "discover", "state", "about"} <= caps
