---
applyTo: "docs/configs/**/*.yml,include/**/*.py,dags/**/*.yml"
---

# Ingestion Config & Pipeline Rules

When writing or reviewing ingestion YAML configs or pipeline task code, follow the rules below.

## Config Validation Rules

Required keys: `file.remote_directory`, `file.local_directory`, `format.type`, `connection.conn_id`, and one of `file.name` / `file.name_regex` (mutually exclusive).
- `schema` is required when `has_header: false`
- `bad_records_path` is required when `bad_records.handling == move`
- `file.name` and `file.name_regex` are mutually exclusive

## Format Types

| `format.type` | Notes |
|---|---|
| `delimited` | Requires `delimiter`; use `quotechar` for quote-enclosed fields |
| `fixed` | Requires `start`/`end` OR `width` per column in schema |
| `json` | Use `source_name` in schema to map JSON keys |
| `xml` | Use `source_name` to map XML element names |

## Schema Column Keys

`name`, `type` (string/integer/float/boolean/date/datetime), `not_null`, `min`, `max`, `min_length`, `max_length`, `regex`, `allowed_values`, `unique`, `date_format` (strftime), `source_name` (JSON/XML key), `start`/`end` (fixed-width byte positions, 1-based).

## Filename Pattern Syntax

- `{timestamp}` placeholder expands to `timestamp_pattern` (strftime)
- Regex fragments inline: `{[A-Z]+}` inside `name_pattern`
- `name_pattern_selection: latest` picks the most recent match; `all` picks all matches

## Encoding Mapping (pandas)

| Config | pandas |
|---|---|
| `UTF-16-BOM` | `utf-16` |
| `ANSI` | `cp1252` |
| `UTF-8` | `utf-8` |

## Task Code Rules

- DataFrames must never be placed in XCom — only file paths (Parquet)
- Intermediate files: `raw.parquet` → `skipped.parquet` → `good.parquet` / `bad.parquet` → `output.parquet`
- All config access via `load_ingestion_config()` from `include/tasks/config_loader.py` (planned)
- Cast with `errors='coerce'`; track NaN-introduced rows as bad records
- Bad-record threshold check before writing output — raise `AirflowException` if exceeded

See [config-writing-guide.md](../../docs/ingestion/config-writing-guide.md) for full reference and [ingestion-plan.prompt.md](../../docs/ingestion/ingestion-plan.prompt.md) for implementation details.
