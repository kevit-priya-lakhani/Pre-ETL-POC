# Plan: Config-Driven SFTP Ingestion Pipeline

## TL;DR
Build a single Airflow DAG (`dags/sftp_ingestion.py`) that accepts a `config_path` param pointing to an ingestion YAML at runtime. All logic lives in `include/tasks/` as plain Python callables. The pipeline: validate config → wait/discover file on SFTP → download → parse (CSV/FWF) → skip-condition → cast+validate → filter → [bad-record handling ‖ output Parquet].

No Pydantic (not in requirements.txt). Plain-dict validation. DataFrames never go in XCom — only file paths (intermediate Parquet files).

---

## Phases

### Phase 1 — Config Loader (new file)
**`include/tasks/config_loader.py`**
- `load_ingestion_config(config_path: str) -> dict`
  - Reads YAML (PyYAML, bundled with Airflow)
  - Validates required keys: `file.remote_directory`, `file.local_directory`, one of `file.name`/`file.name_regex`, `format.type`, `connection.conn_id`
  - Conditional checks: `schema` required when `has_header: false`; `bad_records_path` required when `bad_records.handling == move`; `name` and `name_regex` mutually exclusive
  - Raises `ValueError` with descriptive message on any violation
  - Returns the dict as-is (no transformation)

### Phase 2 — File Discovery & Download (extend file_ingestion.py)
**`include/tasks/file_ingestion.py`** — add:
- `wait_for_file(config_path: str) -> str`
  - Loads config
  - `name` mode: polls `SFTPHook.path_exists(remote_dir + name)` in a while loop using `sensor.poke_interval` (default 60s) and `sensor.timeout` (default 3600s); raises `AirflowException` on timeout
  - `name_regex` mode: `SFTPHook.list_directory(remote_dir)` → `re.search(pattern, filename)` → first match; raises if none
  - Returns resolved `remote_path` string
- `download_file(config_path: str, remote_path: str) -> str`
  - Adapts existing `ingest_sftp_file` — uses `conn_id` from config, `local_directory` from config
  - Returns `local_path`

### Phase 3 — Parse (extend file_ingestion.py)
**`include/tasks/file_ingestion.py`** — add:
- `parse_file(config_path: str, local_path: str) -> str`
  - Empty file check → apply `empty_file_handling` (skip→return None, log→log+return None, fail→raise)
  - `format.type == delimited`: `pd.read_csv(sep, quotechar, encoding, lineterminator, skiprows, comment, header)`
    - `encoding: UTF-16-BOM` → map to `utf-16`; `ANSI` → map to `cp1252`
  - `format.type == fixed`:
    - Style A (start+end per column): build `colspecs = [(start-1, end), ...]` → `pd.read_fwf(colspecs=...)`
    - Style B (width per column): build `widths = [...]` → `pd.read_fwf(widths=...)`
  - If `has_header: false`, assign column names from `schema[*].name`
  - Writes `<local_directory>/raw.parquet`, returns path

### Phase 4 — Skip Condition (extend file_ingestion.py)
**`include/tasks/file_ingestion.py`** — add:
- `apply_skip_condition(config_path: str, parquet_path: str) -> str`
  - If no `skip_condition` key: pass through (return same path)
  - Reads parquet, coerces all columns to `str` dtype for pre-cast evaluation
  - Evaluates expression using `df.eval()` (boolean mask); rows where mask is True are discarded
  - Writes `<local_directory>/skipped.parquet`, returns path

### Phase 5 — Cast & Validate (new file)
**`include/tasks/validation.py`** — new:
- `cast_and_validate(config_path: str, parquet_path: str) -> dict`
  - For each column in schema: attempt type cast
    - `integer` → `pd.to_numeric(errors='coerce')` + check NaN introduced
    - `float` → same
    - `boolean` → map `true/false/1/0/yes/no` strings (case-insensitive)
    - `date` / `datetime` → `pd.to_datetime(format=date_format, errors='coerce')`
    - `string` → keep as-is
  - Rows that fail cast (produced NaN for non-nullable or wrong type) → flagged as bad
  - Per-column validation rules applied to successfully-cast rows:
    - `not_null`: flag rows where value is NaN/None
    - `min`/`max`: numeric range check
    - `min_length`/`max_length`: `len(str(val))`
    - `regex`: `re.fullmatch(pattern, str(val))`
    - `allowed_values`: value not in list
    - `unique`: flag duplicate values in column (track seen set)
  - Bad-record threshold check: compute percentage or count vs config; raise `AirflowException` if exceeded
  - Writes `<local_directory>/good.parquet` and `<local_directory>/bad.parquet`
  - Returns `{"good_path": ..., "bad_path": ..., "total": N, "bad_count": M, "bad_reasons": [...]}`

### Phase 6 — Filter + Bad Records (parallel, extend file_ingestion.py + validation.py)
- `apply_filter_condition(config_path: str, paths: dict) -> str`  ← in `file_ingestion.py`
  - If no `filter_condition`: return `paths["good_path"]` as-is
  - `df.query(filter_condition)` on `good.parquet`
  - Writes `<local_directory>/output.parquet`, returns path (final pipeline output)
- `handle_bad_records(config_path: str, paths: dict) -> None`  ← in `validation.py`
  - `skip`: no-op
  - `log`: log each row from `bad.parquet` as WARNING
  - `move`: write bad records as CSV to `bad_records_path` (creates dir if needed)

### Phase 7 — DAG Wiring (new file)
**`dags/sftp_ingestion.py`**
- Native Python DAG (not YAML-generated; follows `exampledag.py` pattern)
- `@dag` with `params={"config_path": Param(default="...", type="string")}`
- Tasks wired using `@task` (TaskFlow API) + explicit XCom passing
- Graph:
  ```
  validate_config
    → wait_for_file
      → download_file
        → parse_file
          → apply_skip_condition
            → cast_and_validate
              ├→ apply_filter_condition   (final output path to XCom)
              └→ handle_bad_records       (parallel)
  ```

---

## Files
- `include/tasks/config_loader.py` — **new**
- `include/tasks/validation.py` — **new** (cast + validate + bad-record handler)
- `include/tasks/file_ingestion.py` — **extend** (add phases 2, 3, 4, 6-filter)
- `dags/sftp_ingestion.py` — **new**
- `include/tasks/basic_example_tasks.py` — untouched
- `simple_file_transfer.yml` — kept as-is (legacy reference)

---

## Verification
1. Unit test `config_loader.py` with a minimal valid dict → no error; missing required key → `ValueError`
2. Unit test `cast_and_validate` with a 3-row DataFrame containing one bad row per rule type → correct good/bad split
3. Run `sftp_ingestion` DAG in Airflow UI with `config_path` = `docs/example_ingestion_config.yml` and `data/input/top_directors_data.csv` on the SFTP container
4. Confirm `output.parquet` exists at `<local_directory>`, bad records moved to `bad_records_path`

---

## Decisions
- No Pydantic (not in requirements); plain-dict validation in config_loader
- `wait_for_file` uses a while-loop/sleep inside PythonOperator (not real SFTPSensor) to keep runtime config loading; occupies a worker slot — acceptable for POC
- All intermediate stages write named Parquet files under `local_directory`; XCom carries only string paths
- `skip_condition` evaluated before type-casting (on string frame); uses `df.eval()` not `df.query()` to avoid pandas query parser quirks with string comparisons
- `name_regex` mode does NOT poll — it lists and finds once; if file is absent the task fails (no retry loop)
- Existing `upsert_sftp_connection` / `validate_sftp_connection` / `ingest_sftp_file` / `read_csv_file` kept intact for backward compatibility with `simple_file_transfer.yml`
