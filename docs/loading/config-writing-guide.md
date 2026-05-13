# Loading Config Writing Guide

> Blueprint: [`example_loading_config.yml`](example_loading_config.yml)

A loading config has two top-level keys. Both are **required**.

```yaml
destination:   # connection-level settings shared across all tables
tables:        # ordered list of independent load operations
```

---

## `destination`

Defines the target system. Credentials are not stored here — they live in Airflow connections. Set `type` first — it controls which other keys are required.

### `type: postgres`

```yaml
destination:
  type: postgres
  connection_id: "postgres_default"   # Airflow connection ID
  schema: "public"                    # default DB schema; can be overridden per table
```

### `type: oracle`

```yaml
destination:
  type: oracle
  connection_id: "oracle_prod"        # Airflow connection ID
  schema: "FINANCE"                   # default schema; can be overridden per table
```

### `type: filesystem`

```yaml
destination:
  type: filesystem
  connection_id: "sftp_output"          # Airflow SFTP connection ID (omit for local filesystem)
  base_path: /output/                  # root directory on the SFTP server (or local path if no connection_id)
  format: parquet                      # default format — parquet | csv | json | tsv
  write_mode: overwrite                # default write mode — overwrite | append
```

When `connection_id` is provided, files are written to the remote SFTP server at `base_path`. When omitted, files are written to the local filesystem.

> `schema` is not used for `filesystem`. `base_path`, `connection_id` (SFTP), `format`, and `write_mode` are not used for `postgres` or `oracle`.

---

## `tables`

An ordered list of load operations. Tables are executed **in the order listed**. Each entry is independent — it has its own source, copy settings, and delete behaviour.

```yaml
tables:
  - source:
      file_id: "..."     # required — every table entry must declare a source
    table: "..."         # required for DB destinations
    # path: "..."        # required for filesystem destinations (in place of table)
    # ... other keys
```

The only keys that are always **required** per entry are `source.file_id` and either `table` (DB) or `path` (filesystem/SFTP). Everything else is optional and documented below.

---

## `source`

References a `file_id` produced by a prior pipeline stage (ingestion, transformation, or aggregation). The file is always a Parquet file at this stage.

```yaml
source:
  file_id: "sales_summary_enriched"
```

---

## `table` / `path`

**DB destinations (`postgres`, `oracle`):** use `table`.

```yaml
table: "sales_summary"
schema: "reporting"          # (optional) overrides destination.schema for this entry only
```

**Filesystem destinations (local or SFTP):** use `path`.

```yaml
path: store_performance/      # appended to destination.base_path
format: csv                   # (optional) overrides destination.format for this entry only
write_mode: append            # (optional) overrides destination.write_mode for this entry only
connection_id: "sftp_alt"     # (optional) overrides destination.connection_id for this entry only
```

Per-entry `connection_id` lets you write different tables to different SFTP servers within the same config.

> `table` and `path` are mutually exclusive.

---

## `copy_mode`  *(DB destinations only)*

Controls how source rows are applied to the destination table.

```yaml
copy_mode: insert_update     # insert_update | update_only
```

| Value | Behaviour |
|-------|-----------|
| `insert_update` | Upsert — insert rows that do not exist, update rows that do (matched by `primary_key`) |
| `update_only` | Only update rows that already exist in the destination; new rows are silently skipped |

`copy_mode` is **required** for DB destinations unless `delete.mode` is `truncate_before_load` (in which case it defaults to `insert_update`).

---

## `primary_key`  *(DB destinations only)*

The list of columns used to match a source row to an existing destination row. Required for `insert_update` and `update_only`.

```yaml
primary_key:
  - account_id
  - product_code
```

> Order does not matter. All listed columns must be present in the (post-mapping) destination row.

---

## `columns`

Controls column mapping between the source Parquet file and the destination table or file. All source columns are mapped **1:1 by name** by default. Only list entries for columns that deviate from this default.

```yaml
columns:
  - source: acct_number
    destination: account_number    # rename: write source column under a different destination name

  - source: open_dt
    destination: open_date         # rename

  - source: internal_flag
    include: false                 # exclude — do not write this column to the destination
```

**Rules:**
- Omitting `destination` when `include` is not `false` is a rename — the source column is written as-is.
- Omitting `include` means `true` (column is written).
- Columns not mentioned at all are included with their original name.

---

## `empty_source_behavior`  *(DB destinations only)*

Defines what happens when a source value is `null` or an empty string for a row that already exists in the destination.

```yaml
empty_source_behavior:
  default: update          # update | leave
  overrides:
    - column: customer_notes
      behavior: leave
    - column: last_modified_by
      behavior: leave
```

| Value | Behaviour |
|-------|-----------|
| `update` | Overwrite the existing destination value with `null` / empty |
| `leave` | Leave the existing destination value unchanged |

`default` applies to every column not listed in `overrides`. Per-column `overrides` take precedence over `default`.

---

## `delete`  *(DB destinations only)*

All delete behaviour is **opt-in**. Set `enabled: true` and choose a `mode`.

```yaml
delete:
  enabled: true
  mode: sync_delete
```

### `mode: sync_delete`

Deletes rows in the destination that are no longer present in the source, matched by `primary_key` (or an explicit `match_key`).

```yaml
delete:
  enabled: true
  mode: sync_delete
  match_key:               # optional — defaults to primary_key
    - account_id
```

### `mode: condition`

Deletes rows from the destination that satisfy a SQL `WHERE` clause. Executed **before** the copy operation.

```yaml
delete:
  enabled: true
  mode: condition
  condition: "status = 'CLOSED' AND closed_date < current_date - interval '1 year'"
```

### `mode: truncate_before_load`

Truncates the entire destination table before any rows are written. Effectively a full reload on every run.

```yaml
delete:
  enabled: true
  mode: truncate_before_load
```

> `truncate_before_load` cannot be combined with `update_only` — the table is empty after truncation so there is nothing to update.

---

## Filesystem-only keys

### `partition_by`

Partitions a Parquet output by the values of one or more columns. Produces a directory tree rather than a single file.

```yaml
partition_by:
  - year
  - month
```

All columns listed in `partition_by` must exist in the source data. Not applicable to `csv`, `json`, or `tsv` formats.

---

## Quick-reference: which keys apply where

| Key | `postgres` | `oracle` | `filesystem` |
|-----|-----------|---------|--------------|
| `connection_id` | required | required | optional (SFTP) |
| `table` | required | required | — |
| `schema` (per-table override) | optional | optional | — |
| `path` | — | — | required |
| `connection_id` (per-table override) | — | — | optional |
| `format` (per-table override) | — | — | optional |
| `write_mode` (per-table override) | — | — | optional |
| `partition_by` | — | — | optional |
| `copy_mode` | required | required | — |
| `primary_key` | required* | required* | — |
| `columns` | optional | optional | optional |
| `empty_source_behavior` | optional | optional | — |
| `delete` | optional | optional | — |

\* Required when `copy_mode` is `insert_update` or `update_only`.

---

## Minimal examples

### Insert/update to Postgres

```yaml
destination:
  type: postgres
  connection_id: "postgres_default"
  schema: "public"

tables:
  - source:
      file_id: "accounts_enriched"
    table: "accounts"
    copy_mode: insert_update
    primary_key:
      - account_id
```

### Full reload (truncate + insert) to Oracle

```yaml
destination:
  type: oracle
  connection_id: "oracle_prod"
  schema: "FINANCE"

tables:
  - source:
      file_id: "product_master_output"
    table: "PRODUCTS"
    copy_mode: insert_update
    delete:
      enabled: true
      mode: truncate_before_load
```

### Write to local filesystem as CSV

```yaml
destination:
  type: filesystem
  base_path: /output/
  format: csv
  write_mode: overwrite

tables:
  - source:
      file_id: "store_performance_output"
    path: store_performance/
```

### Write to SFTP server as CSV

```yaml
destination:
  type: filesystem
  connection_id: "sftp_output"   # Airflow SFTP connection ID
  base_path: /remote/output/
  format: csv
  write_mode: overwrite

tables:
  - source:
      file_id: "store_performance_output"
    path: store_performance/
```

### Multiple tables in one config

```yaml
destination:
  type: postgres
  connection_id: "postgres_default"
  schema: "public"

tables:
  - source:
      file_id: "sales_summary_enriched"
    table: "sales_summary"
    copy_mode: insert_update
    primary_key: [sale_id]

  - source:
      file_id: "product_detail_output"
    table: "products"
    schema: "catalogue"           # overrides destination.schema for this table only
    copy_mode: update_only
    primary_key: [product_code]
    delete:
      enabled: true
      mode: sync_delete
```
