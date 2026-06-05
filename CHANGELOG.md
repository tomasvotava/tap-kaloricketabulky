## 0.1.0 (2026-06-05)

### Feat

- add full-table snapshot streams (energy, nutrients, drink, weight, optional)
- add date-windowed streams and wire tap discovery
- add async-to-sync client bridge with lazy login and re-auth
- generate singer schemas from sdk pydantic models

### Fix

- refresh uv.lock during cz bump so release CI stays locked
- correct meltano.yml and .env.example config and interpret start_date date literally
- resume per-day streams from state bookmark using raw replication value

### Refactor

- **client**: unregister atexit hook on close and simplify date parsing
- adopt StreamSchema descriptor over deprecated schema_filepath
