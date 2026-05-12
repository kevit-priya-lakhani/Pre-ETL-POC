# Pre-ETL POC — Agent Instructions

## Project Overview

Config-driven Apache Airflow ETL pipeline for ingesting files (CSV, fixed-width, JSON, XML) from SFTP servers and applying transformations and aggregations. Still in active development — the ingestion stage is partially implemented; transformations and aggregations are requirements-only.

## Local Development

```bash
astro dev start   # start all 5 Airflow containers (Postgres, Scheduler, DAG Processor, API Server, Triggerer)
astro dev stop    # stop containers
```

- Airflow UI: `http://localhost:8080/`
- SFTP: `localhost:2222` (user: `sftp`, password: `password`)
- Postgres: `localhost:5432` (user: `postgres`, password: `postgres`)

Set up connections by copying `example.env` and configuring `airflow_settings.yaml`.

## Architecture

Three-stage pipeline, all stages are config-driven via YAML:

1. **Ingestion** — Download files from SFTP, parse format, validate schema, filter records
2. **Transformation** — Type casting, date parsing, trimming, null handling, column creation
3. **Aggregation** — File merging, group-by, aggregation functions (min/max/sum/avg/count)

**Directory layout:**

| Path | Purpose |
|------|---------|
| `dags/` | Airflow DAGs (Python + YAML-defined via dag-factory) |
| `include/tasks/` | Reusable task callables imported by DAGs |
| `plugins/` | Custom Airflow plugins (empty for now) |
| `scripts/` | Standalone utility scripts |
| `docs/configs/` | 14 example YAML ingestion configs covering all formats |
| `docs/ingestion/` | Requirements, config-writing guide, and implementation plan |
| `docs/transformations/` | Transformation requirements |
| `docs/aggregations/` | Aggregation requirements |

## Key Conventions

### DAGs

Two patterns are used — choose per task complexity:

- **YAML DAGs** (simple): define in `dags/*.yml`, auto-loaded by [`dags/dag_generation.py`](dags/dag_generation.py) via `dag-factory`
- **Python DAGs** (complex): use the TaskFlow API (`@dag` + `@task` decorators), see [`dags/exampledag.py`](dags/exampledag.py)

### Data Passing Between Tasks

**DataFrames must NOT be placed in XCom.** Pass only file paths (intermediate Parquet files) between tasks. Parquet files live in the `local_directory` specified in the config.

### Task Callables

All task logic lives in `include/tasks/` as plain Python functions. Import them into DAGs — do not embed business logic inside the DAG file itself.

### Type Conversion

No Pydantic. Use plain-dict validation with `PyYAML`. Type casting uses `pandas` (`pd.to_numeric`, `pd.to_datetime`, etc.) with `errors='coerce'` and explicit bad-record tracking.

### Encoding Mapping

| Config value | Pandas equivalent |
|---|---|
| `UTF-16-BOM` | `utf-16` |
| `ANSI` | `cp1252` |

## Configuration Files

Ingestion configs are YAML files with six top-level keys: `file`, `format`, `schema`, `filter_condition`, `min_record_threshold`, `bad_records`.

- **Config-writing guide**: [`docs/ingestion/config-writing-guide.md`](docs/ingestion/config-writing-guide.md) — canonical reference for all keys and values
- **Example configs**: [`docs/configs/`](docs/configs/) — 14 real examples covering all formats and edge cases
- **Ingestion requirements**: [`docs/ingestion/requirements.md`](docs/ingestion/requirements.md)
- **Transformation requirements**: [`docs/transformations/requirements.md`](docs/transformations/requirements.md)
- **Aggregation requirements**: [`docs/aggregations/requirements.txt`](docs/aggregations/requirements.txt)

## Implementation Plan

The ingestion pipeline implementation plan (7 phases, function signatures, XCom strategy, error handling) is in [`docs/ingestion/ingestion-plan.prompt.md`](docs/ingestion/ingestion-plan.prompt.md). Follow it when implementing new ingestion tasks.

Planned new files:
- `include/tasks/config_loader.py` — YAML config validation
- `include/tasks/validation.py` — cast + validate + bad-record handling
- `dags/sftp_ingestion.py` — main ingestion DAG

## Testing

Tests live in `tests/dags/`. Run with pytest (Python environment at `scripts/.venv`).

## Dependencies

- Runtime: `requirements.txt` (Airflow providers: SFTP; dag-factory)
- Scripts: `scripts/pyproject.toml` (DuckDB ≥1.2.5, pandas ≥3.0.2, PyYAML ≥6.0.3, NumPy ≥2.4.4)
- OS packages: `packages.txt`
- Docker image: `astrocrpublic.azurecr.io/runtime:3.2-3` (Airflow 3.x, Python 3.12+)
