# tap-kaloricketabulky

A Singer tap (Meltano SDK) for extracting a user's own data from
[kaloricketabulky.cz](https://www.kaloricketabulky.cz). Built on the
[kaloricketabulky-sdk](https://github.com/tomasvotava/kaloricketabulky).

> The site has no official public API. This tap uses the same unofficial endpoints the
> web app uses. Use it for your own data only, be a respectful guest: keep
> `request_delay_seconds` at 0.5 s or higher and don't hammer the site. If you get
> value from kaloricketabulky.cz, consider
> [supporting them with a subscription](https://www.kaloricketabulky.cz/user/premium/public).

## Requirements

- Python >= 3.12
- [uv](https://docs.astral.sh/uv/)

## Configuration

Settings can be supplied via a `config.json` file or as environment variables prefixed
`TAP_KALORICKETABULKY_` (the standard Meltano/Singer SDK convention).

| Setting | Required | Type | Default | Description |
|---|---|---|---|---|
| `email` | yes | string (secret) | — | Login e-mail address |
| `password` | yes | string (secret) | — | Login password |
| `start_date` | yes | date-time | — | Earliest day to extract (ISO 8601, e.g. `2025-01-01T00:00:00Z`) |
| `end_date` | no | date-time | today | Latest day to extract |
| `lookback_days` | no | integer | `3` | Days before the bookmark to re-pull on each run |
| `request_delay_seconds` | no | float | `0.5` | Seconds to wait between API requests |
| `base_url` | no | string | `https://www.kaloricketabulky.cz` | Override the API base URL |
| `user_agent` | no | string | SDK default | Override the `User-Agent` request header |

## Streams

### Per-day — INCREMENTAL (replication key: `date`)

| Stream | SDK method |
|---|---|
| `diary` | `get_diary` |
| `diary_summary` | `get_diary_summary` |
| `statistics_summary` | `get_statistics_summary` |
| `streak` | `get_streak` |

### Snapshots — FULL_TABLE

| Stream | Metric |
|---|---|
| `snapshot_energy` | energy |
| `snapshot_nutrients` | nutrients |
| `snapshot_drink` | drink |
| `snapshot_weight` | weight |
| `snapshot_optional` | user-defined custom metrics |

Records are emitted faithfully and with nested structure matching the SDK models. To flatten
nested fields into columns, enable the SDK's built-in flattener via
`flattening_enabled: true` and `flattening_max_depth: <n>` in your config.

## Incremental and lookback behaviour

Per-day streams resume from Singer state. On each run, the tap re-pulls the last
`lookback_days` days before the stored bookmark so that late diary entries (people
often log calories a day or two after the fact) are captured without a full backfill.

Snapshot streams are FULL_TABLE: each run pulls the complete `[start_date, today]`
series in a single request per metric, so late edits to past days are always reflected.
Dedup downstream by measurement day if needed.

Lowering `start_date` after the first run requires resetting Singer state to backfill
the newly included range (standard Singer behaviour).

## Usage

### CLI

```bash
uv run tap-kaloricketabulky --about --format=json
uv run tap-kaloricketabulky --config config.json --discover > catalog.json
uv run tap-kaloricketabulky --config config.json --catalog catalog.json
```

### Meltano

```yaml
plugins:
  extractors:
  - name: tap-kaloricketabulky
    namespace: tap_kaloricketabulky
    pip_url: git+https://github.com/tomasvotava/tap-kaloricketabulky.git
    capabilities:
    - state
    - catalog
    - discover
    - about
    - stream-maps
    settings:
    - name: email
      kind: password
      label: Email
    - name: password
      kind: password
      label: Password
    - name: start_date
      kind: date_iso8601
      label: Start Date
    settings_group_validation:
    - [email, password, start_date]
    config:
      start_date: "2025-01-01T00:00:00Z"
      request_delay_seconds: 0.5
```

## Development

```bash
uv sync                                    # create the environment from the lockfile
uv run ruff format --check .               # check formatting
uv run ruff check .                        # lint
uv run mypy tap_kaloricketabulky tests     # strict type-check
uv run pytest                              # run tests with coverage
uv run python scripts/gen_schemas.py       # regenerate schemas from SDK models
```

Never hand-edit the JSON files under `tap_kaloricketabulky/schemas/`; they are generated
from the SDK's Pydantic models. A drift test (`tests/test_schemas.py`) fails the suite if
the committed schemas fall out of sync with the models.

## Releases

Versioning and the changelog are driven by
[Commitizen](https://commitizen-tools.github.io/commitizen/).
Do not edit `CHANGELOG.md` by hand:

```bash
uv run cz bump
```

## License

MIT
