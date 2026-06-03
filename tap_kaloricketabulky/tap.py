"""Kaloricketabulky tap class."""

from __future__ import annotations

from singer_sdk import Stream, Tap
from singer_sdk import typing as th


class TapKaloricketabulky(Tap):
    """Singer tap for kaloricketabulky.cz."""

    name = "tap-kaloricketabulky"

    config_jsonschema = th.PropertiesList().to_dict()

    def discover_streams(self) -> list[Stream]:
        """Return the tap's streams (populated during implementation)."""
        return []


if __name__ == "__main__":
    TapKaloricketabulky.cli()
