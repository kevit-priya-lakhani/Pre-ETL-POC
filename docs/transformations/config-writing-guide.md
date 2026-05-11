# Transformation Config Writing Guide

> Blueprint: [`example_transformation_config.yml`](example_transformation_config.yml)

A transformation config has the following top-level keys.

```yaml
source: <ingestion_config.yml>   # (required) reference to the ingestion config; used for validation and to resolve source_name mappings in the schema
columns: ~                       # (optional) per-column transformations applied to existing columns; ~ means no transformations
new_columns: ~                   # (optional) derived/computed columns appended to the output; ~ means no new columns
```

Transformations inside `columns` are executed **in the order listed**. All expressions compile to DuckDB SQL.

---

## `source`
**Required.** A reference to the ingestion config that produced the input data. Used for validation and to resolve `source_name` references in the `schema` (if present).

---

## `columns`

A list of column entries. Each entry names an existing column and declares an ordered list of `transformations` to apply to it.

```yaml
columns:
  - name: <column_name>
    transformations:
      - type: <transformation_type>
        # ... type-specific keys
```

### `type: trim`

Removes leading and/or trailing whitespace.

```yaml
- type: trim
  side: both          # both | left | right
```


---

### `type: cast`

Converts the column to a target SQL type. Uses `TRY_CAST` — rows where the cast fails become `NULL` and are subject to `null_handling` or bad-record rules downstream.

```yaml
- type: cast
  to: integer         # string | integer | float | boolean | date | datetime
```

---

### `type: round`

Rounds a numeric column to a fixed number of decimal places.

```yaml
- type: round
  decimal_places: 2   # 0 for whole numbers
```


---

### `type: date_conversion`

Parses a *string* column that may contain dates in one of several formats and outputs a single canonical format. Formats are tried in order; the first non-`NULL` result is used.

```yaml
- type: date_conversion
  source_formats:         # tried in order; first match wins
    - "%d/%m/%Y"
    - "%m-%d-%Y"
    - "%Y%m%d"
  target_format: "%Y-%m-%d"   # output format (ISO 8601 recommended)
```

**Common `strftime` patterns:**

| Pattern | Example input |
|---------|--------------|
| `"%Y%m%d"` | `20260410` |
| `"%Y-%m-%d"` | `2026-04-10` |
| `"%d/%m/%Y"` | `10/04/2026` |
| `"%d-%b-%Y"` | `10-Apr-2026` |

---

### `type: substring`

Extracts a portion of a string column by position or regex pattern.

**By position:**
```yaml
- type: substring
  mode: position
  start: 1            # 1-based index
  length: 50
```

**By pattern (first regex capture group):**
```yaml
- type: substring
  mode: pattern
  pattern: "^([^.]+)\."    # extracts text before the first period
```
---

### `type: case_conversion`

Converts string values to upper or lower case.

```yaml
- type: case_conversion
  to: upper           # upper | lower
```

---

### `type: remove_non_printable`

Strips or replaces non-printable control characters (outside the ASCII printable range `0x20–0x7E`).

**Remove non-printable characters (default — replace with empty string):**
```yaml
- type: remove_non_printable
```

**Replace non-printable characters with a fixed value:**
```yaml
- type: remove_non_printable
  replace_with: " "    # optional; omit to remove (replace with "")
```

> `replace_with` is optional. When omitted, matched characters are removed (replaced with `""`).

---

### `type: null_handling`

Controls what happens when a column value is `NULL` (or becomes `NULL` after a failed `cast`). Optionally also treats empty strings and whitespace-only strings the same as `NULL` by setting `include_empty: true`.

**Replace with a default value:**
```yaml
- type: null_handling
  strategy: replace
  replace_with: "UNKNOWN"   # must match the column type
```

**Also treat empty / whitespace-only strings as null (replace):**
```yaml
- type: null_handling
  strategy: replace
  replace_with: "UNKNOWN"
  include_empty: true        # optional; default false — also catches '' and '   '
```


**Drop the entire row if the column is null:**
```yaml
- type: null_handling
  strategy: drop_row
```

**Also drop rows where the column is empty / whitespace-only:**
```yaml
- type: null_handling
  strategy: drop_row
  include_empty: true        # optional; default false
```

---

## `new_columns`

A list of derived column definitions. Each entry is appended to the output in the order listed.

```yaml
new_columns:
  - name: <output_column_name>
    type: <output_type>          # string | integer | float | boolean | date | datetime
    value: <strategy>
    # ... strategy-specific keys
```

### `value: fixed`

A constant value for every row.

```yaml
- name: source_system
  type: string
  value: fixed
  fixed_value: "DIRECTORS"
```

DuckDB: `SELECT 'DIRECTORS' AS source_system`

---

### `value: expression`

A raw DuckDB SQL expression referencing any existing column.

```yaml
- name: revenue_per_film
  type: float
  value: expression
  expression: "ROUND(gross_revenue / NULLIF(film_count, 0), 2)"
```



---

### `value: arithmetic`

Shorthand for a simple arithmetic expression. Functionally identical to `value: expression`.

```yaml
- name: adjusted_revenue
  type: float
  value: arithmetic
  expression: "gross_revenue * 1.05"
```

---

### `value: concat`

Joins columns and/or literal strings with a separator, ignoring `NULL` parts.

```yaml
- name: display_label
  type: string
  value: concat
  separator: " — "
  parts:
    - column: director_name    # reference an existing column
    - column: debut_date
    - literal: "(director)"    # fixed string fragment
```

---

### `value: conditional`

Produces a value based on a `CASE WHEN` expression. Cases are evaluated top-to-bottom; the first matching `when` wins.

```yaml
- name: tier
  type: string
  value: conditional
  cases:
    - when: "film_count >= 20"
      then: "Prolific"
    - when: "film_count >= 10"
      then: "Active"
    - when: "film_count >= 1"
      then: "Emerging"
  else: "Unknown"            # required fallback; use null to emit NULL
```

---

### Combining transformations inline

When a new column's value depends on functions applied to an existing column, you can embed DuckDB functions directly inside a `value: expression` or `value: conditional` expression rather than adding a separate `columns` entry.

**Example — `TRY_CAST(TRIM(…))` + conditional logic referencing `column1` and `column2`:**
```yaml
- name: derived_value
  type: string
  value: expression
  expression: "CASE WHEN TRY_CAST(TRIM(column1) AS INTEGER) > 5 THEN '0' ELSE column2 END"
```

---

### `value: uuid`

Generates a unique random UUID for every row.

```yaml
- name: record_id
  type: string
  value: uuid
```


---

### `value: date_function`

Extracts a date component or performs date arithmetic.

**Extract year / month / day / day_of_week:**
```yaml
- name: debut_year
  type: integer
  value: date_function
  function: year             # year | month | day | day_of_week
  source_column: debut_date
```

**Day of week (1 = Sunday … 7 = Saturday):**
```yaml
- name: debut_day_of_week
  type: integer
  value: date_function
  function: day_of_week
  source_column: debut_date
```


---

## Quick reference

### Column transformation types

| `type` | Key parameters | DuckDB |
|--------|---------------|--------|
| `trim` | `side: both\|left\|right` | `TRIM` / `LTRIM` / `RTRIM` |
| `cast` | `to: <type>` | `TRY_CAST(col AS type)` |
| `round` | `decimal_places: N` | `ROUND(col, N)` |
| `date_conversion` | `source_formats`, `target_format` | `TRY_CAST(strptime(…) AS DATE)` |
| `substring` | `mode: position` → `start`, `length` | `SUBSTRING(col, start, length)` |
| `substring` | `mode: pattern` → `pattern` | `regexp_extract(col, pattern, 1)` |
| `case_conversion` | `to: upper\|lower` | `UPPER` / `LOWER` |
| `remove_non_printable` | `replace_with` (optional, default `""`) | `regexp_replace(col, '[^\x20-\x7E]', replace_with, 'g')` |
| `null_handling` | `strategy: replace` → `replace_with`, `include_empty` (opt) | `COALESCE(col, default)` / `COALESCE(NULLIF(TRIM(col), ''), default)` |
| `null_handling` | `strategy: drop_row`, `include_empty` (opt) | `WHERE col IS NOT NULL` / `WHERE col IS NOT NULL AND TRIM(col) <> ''` |

### New column strategies

| `value` | Key parameters | DuckDB |
|---------|---------------|--------|
| `fixed` | `fixed_value` | literal constant |
| `expression` | `expression` | raw SQL expression |
| `arithmetic` | `expression` | raw SQL expression |
| `concat` | `separator`, `parts[]` | `concat_ws(sep, …)` |
| `conditional` | `cases[]` (`when`/`then`), `else` | `CASE WHEN … END` |
| `uuid` | _(none)_ | `gen_random_uuid()` |
| `date_function` `year\|month\|day\|day_of_week` | `function`, `source_column` | `YEAR()` / `MONTH()` / `DAY()` / `DAYOFWEEK()` |
