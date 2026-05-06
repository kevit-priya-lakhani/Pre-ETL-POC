# Ingestion Config Writing Guide

> Blueprint: [`example_ingestion_config.yml`](../example_ingestion_config.yml)

A config file has six top-level keys. `file`, `format`, and `bad_records` are **required**.

```yaml
file:                  # where the file lives and how to find it
format:                # how to parse the bytes into rows and columns
min_record_threshold:  # (optional) guard against unexpectedly empty files
filter_condition:      # (optional) SQL row filter applied after reading
schema:                # (optional*) column names, types, and validation
bad_records:           # what to do when a row fails validation
```

---

## `file`

```yaml
file:
  remote_directory: /sftp/incoming/

  name: accounts_20240601.csv          # exact filename  ─┐ use one,
  # OR                                                     │ not both
  name_pattern: "Account_{timestamp}.csv"                # ─┘
  timestamp_pattern: "%Y%m%d_%H%M%S"  # required when pattern has {timestamp}
  name_pattern_selection: latest       # latest (default) | all
```

**`name_pattern_selection`** — `latest` picks the newest file; `all` processes every match (use for delta/catch-up loads).

**`timestamp_pattern`** uses Python `strftime` codes:

| Pattern | Matches |
|---------|---------|
| `%Y%m%d_%H%M%S` | `20260410_090000` |
| `%Y%m%d %H%M%S` | `20251219 103000` |
| `%Y-%m-%d` | `2026-04-10` |

---

## `format`

Set `type` first — it controls which other keys are relevant.

### `type: delimited` — CSV, pipe, tab, semicolon

```yaml
format:
  type: delimited
  delimiter: ","           # "," | "|" | "\t" | ";"
  enclosing_character: '"' # omit or set null if no quoting
  encoding: UTF-8
  line_ending: "\n"        # "\n" | "\r\n"
  has_header: true
  skip_rows: 0             # rows to skip before header/data
  comment_prefix: "#"      # rows starting with this are discarded
```

> **Encoding note:** `UTF-16`, `UTF-16-BOM`, and `ANSI` must be pre-decoded to UTF-8 in Python before passing to DuckDB.

**`skip_rows_by_file`** — use instead of `skip_rows` when different files need different counts:

```yaml
  skip_rows_by_file:
    - filename: "feed_2024_02.csv"
      skip_rows: 2
    - filename: "feed_2024_03.csv"
      skip_rows: 1
```

### `type: fixed` — fixed-width positional files

```yaml
format:
  type: fixed
  encoding: UTF-8
  line_ending: "\n"
  has_header: true
  skip_rows: 1        # skip preamble rows
  comment_prefix: "#"
```

Column positions are set **per field** in `schema` via `start` / `end` (see [Schema](#schema)).

### `type: json`

```yaml
format:
  type: json
  encoding: UTF-8
  structure: array    # array | object | lines
```

| `structure` | Meaning |
|-------------|---------|
| `array` | `[ { … }, { … } ]` |
| `object` | Single JSON object (one record) |
| `lines` | Newline-delimited JSON (NDJSON) |

### `type: xml`

```yaml
format:
  type: xml
  encoding: UTF-8
  root_element: accounts   # top-level wrapper element
  record_element: record   # repeating element — one per row
```

> `has_header`, `delimiter`, `skip_rows`, and `comment_prefix` are **not used** for `json` or `xml`.

---

## `min_record_threshold`

```yaml
min_record_threshold: 1   # default: 0 (empty files allowed)
```

Raises an exception if the file has fewer data rows than this value. Set to `0` to explicitly allow empty files.

---

## `filter_condition`

```yaml
filter_condition: "amount > 0 AND currency = 'EUR'"
```

A DuckDB SQL `WHERE` clause applied **after** type casting. Only matching rows continue downstream. Common uses:

- Filter by record type in mixed-type files: `record_type = 'ACC'`
- Drop zero/empty rows: `amount > 0`
- Subset by dimension: `currency = 'EUR'`

---

## `schema`

A list of column definitions. **Required when** `has_header: false`, `type: fixed`, or `type: json`/`xml`. Optional for delimited files with a header (use to add casting or validation).

```yaml
schema:
  - name: open_date          # output column name
    type: date               # string | integer | float | boolean | date | datetime
    source_name: "Contract Date"  # JSON key or XML tag — only needed when it differs from name
    date_format: "%Y%m%d"    # required for date/datetime fields

    # Fixed-width only
    start: 1                 # 1-based, inclusive
    end: 10

    # Validation (all optional)
    not_null: true
    min_length: 2            # string
    max_length: 100          # string
    regex: "^[A-Z]+$"        # string — DuckDB regexp_matches pattern
    min: 0                   # integer / float
    max: 9999                # integer / float
    unique: true             # flag duplicate values
    allowed_values: [A, B, C]  # enum — values outside list are bad records
```

**`date_format`** common patterns:

| Format | Example |
|--------|---------|
| `"%Y%m%d"` | `20260410` |
| `"%Y-%m-%d"` | `2026-04-10` |
| `"%d/%m/%Y"` | `10/04/2026` |

---

## `bad_records`

Any row that fails type casting or a validation rule is a bad record.

```yaml
bad_records:
  handling: move          # skip | move | fail
  threshold: 10
  threshold_type: percentage   # percentage | count
```

| `handling` | Behaviour |
|------------|-----------|
| `skip` | Discard silently |
| `move` | Copy to a separate bad-records CSV |
| `fail` | Raise `AirflowException` when threshold is breached |

| `threshold_type` | Triggers when… |
|------------------|----------------|
| `percentage` | bad rows > N % of total |
| `count` | bad row count > N |

---

## Quick reference

| Key | Required | Type | Default |
|-----|----------|------|---------|
| `file.remote_directory` | yes | all | — |
| `file.name` / `name_pattern` | yes (one) | all | — |
| `file.timestamp_pattern` | if `{timestamp}` in pattern | all | — |
| `file.name_pattern_selection` | no | all | `latest` |
| `format.type` | yes | all | — |
| `format.delimiter` | yes | delimited | — |
| `format.enclosing_character` | no | delimited | none |
| `format.structure` | yes | json | — |
| `format.root_element` | yes | xml | — |
| `format.record_element` | yes | xml | — |
| `format.encoding` | no | delimited, fixed | `UTF-8` |
| `format.line_ending` | no | delimited, fixed | `"\n"` |
| `format.has_header` | no | delimited, fixed | `true` |
| `format.skip_rows` | no | delimited, fixed | `0` |
| `format.comment_prefix` | no | delimited, fixed | none |
| `min_record_threshold` | no | all | `0` |
| `filter_condition` | no | all | none |
| `schema[].name` | yes | all | — |
| `schema[].type` | yes | all | — |
| `schema[].source_name` | no | json, xml | — |
| `schema[].start` + `end` | yes | fixed | — |
| `schema[].date_format` | yes | date/datetime | — |
| `bad_records.handling` | yes | all | — |
| `bad_records.threshold` | yes | all | — |
| `bad_records.threshold_type` | yes | all | — |
