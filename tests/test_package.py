"""Smoke test that the package imports and exposes the tap class."""

from __future__ import annotations

from tap_kaloricketabulky.tap import TapKaloricketabulky


def test_tap_class_is_importable() -> None:
    assert TapKaloricketabulky.name == "tap-kaloricketabulky"
