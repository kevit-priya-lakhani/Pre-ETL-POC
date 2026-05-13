# Aggregation Config Writing Guide

> Blueprint: [`example_aggregation_config.yml`](example_aggregation_config.yml)

An aggregation config has two top-level keys. Both are **required**.

```yaml
outputs:    # declares which file_ids are terminal (handed to the DB copy stage)
tasks:      # ordered list of merge, aggregation, column_transformation, and validation tasks
```

---

## Execution model

Tasks run **sequentially, top to bottom**. Each task reads from a `source.file_id` (or `sources` for merges) and writes to a `destination.file_id`. A `file_id` produced by one task can be read by any later task — including by **multiple tasks in parallel branches** (fan-out).

```
TASK 1: merge ──────────────────► merged_output  (intermediate)
                                        │
              ┌─────────────────────────┼──────────────────────┐
              ▼                         ▼                      ▼
TASK 2: column_transformation   TASK 3: aggregation   TASK 4: aggregation
     branch_a_output [T]          agg_raw (i)           branch_c_output [T]
                                        │
                                        ▼
                                  TASK 5: column_transformation
                                    branch_b_output [T]
```

`[T]` = terminal (listed in `outputs`) — `(i)` = intermediate (not listed)

The shared intermediate (`merged_output`) is a Parquet file read once per consuming task — cheap on disk.

---

## `outputs`

Declares the `file_id`s that the DB copy stage (`job.yml`) will consume. Intermediate `file_id`s that are only used within this config are **not** listed here.

```yaml
outputs:
  - file_id: "product_detail_output"   # → Product table
  - file_id: "customer_agg_output"     # → Customer table
  - file_id: "store_summary_output"    # → StorePerformance table
```

> Every `file_id` listed in `outputs` must be produced by exactly one task in `tasks`.

---

## `tasks`

A list of task definitions. Each task has a `task_id`, a `type`, and an optional `description`.

```yaml
tasks:
  - task_id: "my_task"         # unique identifier within this config
    type: merge                # merge | aggregation | column_transformation | validation
    description: "..."         # optional, free text
    # ... type-specific keys
```

### `type` values

| `type` | Description |
|--------|-------------|
| `merge` | Combines two or more source datasets using union or join operations |
| `aggregation` | Groups rows by one or more keys and applies aggregation functions |
| `column_transformation` | Applies per-column transforms and derives new columns on an existing dataset |
| `validation` | Runs assertions against a dataset; pass-through on success |

---

## Task type: `merge`

Combines two or more source `file_id`s using union or join operations. The first source is the base table for all subsequent joins.

```yaml
- task_id: "merged_sales"
  type: "merge"

  sources:
    - file_id: "regional_sales_north"  # file_id declared in job.yml or a prior task's destination
      alias: "north"                   # short name used in joins below
      prefix: "n_"                     # optional — prepended to ambiguous column names
      columns: ["store_id", "product_id", "sale_date", "quantity", "revenue"]

    - file_id: "regional_sales_south"
      alias: "south"
      prefix: "s_"
      columns: ["store_id", "product_id", "sale_date", "quantity", "revenue"]

    - file_id: "product_master"
      alias: "prod"
      prefix: "p_"
      columns: ["product_id", "product_name", "category"]

  joins:
    - type: "union_all"           # union_all | union_distinct
      left: "north"               # alias of left source
      right: "south"              # alias of right source
      result_alias: "all_sales"   # alias for downstream joins in this list
      column_mapping:             # optional — explicit column alignment for union
        - left_col: "store_id"
          right_col: "store_id"

    - type: "left"                # left | right | inner | full | cross | semi | anti
      left: "all_sales"
      right: "prod"
      on:
        - left_col: "product_id"
          right_col: "product_id"
          operator: "equal"       # equal | not_equal | greater_than | less_than | greater_than_or_equal | less_than_or_equal

  filters:                        # optional — applied after all joins
    mode: "include"               # include | exclude
    combine: "AND"                # AND | OR
    conditions:
      - column: "sale_date"
        operator: "greater_than_or_equal"
        value: "2025-01-01"
      - column: "category"
        operator: "in"
        value: ["Electronics", "Clothing"]

  deduplicate:                    # optional — applied after filters
    enabled: true
    on_columns: ["store_id", "product_id", "sale_date"]
    keep: "first"                 # first | last | none (drop all duplicates)
    order_by:
      - column: "sale_date"
        direction: "desc"         # asc | desc

  destination:
    file_id: "merged_sales_output"
```

### Join types

| `type` | Behaviour |
|--------|-----------|
| `union_all` | Append rows from right onto left (keeps duplicates) |
| `union_distinct` | Append rows, deduplicate the combined result |
| `inner` | Keep only rows with a match on both sides |
| `left` | Keep all left rows; `NULL` fill when right has no match |
| `right` | Keep all right rows; `NULL` fill when left has no match |
| `full` | Keep all rows from both sides; `NULL` fill for missing matches |
| `cross` | Cartesian product — omit `on` for cross joins |
| `semi` | Keep left rows that have at least one match on the right |
| `anti` | Keep left rows that have **no** match on the right |

### `on` operators

| `operator` | Meaning |
|------------|---------|
| `equal` | Left column value = right column value |
| `not_equal` | Left column value ≠ right column value |
| `greater_than` | Left column value > right column value |
| `less_than` | Left column value < right column value |
| `greater_than_or_equal` | Left column value ≥ right column value |
| `less_than_or_equal` | Left column value ≤ right column value |

For composite join keys, add more entries to `on`. For cross joins, omit `on` entirely.

### `filters` — `mode`

| `mode` | Behaviour |
|--------|-----------|
| `include` | Keep only rows that satisfy the conditions |
| `exclude` | Drop rows that satisfy the conditions |

### `filters` — `combine`

| `combine` | Behaviour |
|-----------|-----------|
| `AND` | Every condition in the list must be satisfied |
| `OR` | At least one condition in the list must be satisfied |

### `filters` — `conditions[].operator`

| `operator` | `value` field | Example |
|------------|---------------|---------|
| `equal` | scalar | `value: "ACC"` |
| `not_equal` | scalar | `value: "PAY"` |
| `greater_than` | number | `value: 100` |
| `less_than` | number | `value: 100` |
| `greater_than_or_equal` | number | `value: 0` |
| `less_than_or_equal` | number | `value: 9999` |
| `in` | list | `value: ["ACC", "PAY"]` |
| `not_in` | list | `value: ["CANCELLED"]` |
| `between` | two-element list `[min, max]` | `value: [0, 1000]` |
| `is_null` | *(omit value)* | — |
| `is_not_null` | *(omit value)* | — |
| `like` | SQL LIKE pattern string | `value: "ACC%"` |

The same `filters` syntax (with the same operators) is used in the `having` key for post-aggregation filtering.

### `deduplicate.keep`

| `keep` | Behaviour |
|--------|-----------|
| `first` | Retain the first row within each duplicate group (determined by `order_by`) |
| `last` | Retain the last row within each duplicate group |
| `none` | Drop **all** rows in a duplicate group |

### `deduplicate.order_by` — `direction`

| `direction` | Meaning |
|-------------|---------|
| `asc` | Ascending — smallest / earliest value first; determines which row is treated as "first" |
| `desc` | Descending — largest / latest value first; determines which row is treated as "last" |

---

## Task type: `aggregation`

Groups rows by one or more keys and applies aggregation functions to produce summary columns.

```yaml
- task_id: "agg_by_category_month"
  type: "aggregation"

  source:
    file_id: "merged_sales_output"   # any file_id produced by a prior task or declared in job.yml

  group_by:
    - column: "category"
    - expression: "DATE_TRUNC('month', sale_date)"  # raw DuckDB expression
      alias: "sale_month"                           # required when using expression

  aggregations:
    - function: "sum"        # see aggregation functions below
      column: "revenue"
      alias: "total_revenue"

    - function: "first"
      column: "sale_date"
      alias: "earliest_sale"
      order_by:              # required for first | last
        - column: "sale_date"
          direction: "asc"

  having:                    # optional — filter on aggregated values (same syntax as filters)
    mode: "include"
    combine: "AND"
    conditions:
      - column: "total_revenue"
        operator: "greater_than"
        value: 1000

  order_by:                  # optional — sort the output
    - column: "sale_month"
      direction: "asc"
    - column: "total_revenue"
      direction: "desc"

  limit: null                # optional — null means no limit; integer caps the output row count

  destination:
    file_id: "sales_summary_raw"
```

### Aggregation functions

| `function` | Description | `order_by` required |
|------------|-------------|---------------------|
| `min` | Minimum value | no |
| `max` | Maximum value | no |
| `sum` | Sum of values | no |
| `avg` | Arithmetic mean | no |
| `count` | Row count (use `column: "*"` to count all rows) | no |
| `count_distinct` | Count of unique non-null values | no |
| `first` | Value from the first row in the ordered group | **yes** |
| `last` | Value from the last row in the ordered group | **yes** |
| `median` | Middle value | no |
| `stddev` | Standard deviation | no |
| `variance` | Statistical variance | no |
| `list_agg` | Concatenate values into a list | no |
| `string_agg` | Concatenate values into a delimited string | no |

`first` and `last` require an `order_by` sub-key to define which row is "first" or "last" within each group.

### `group_by` — column vs expression

```yaml
group_by:
  - column: "store_id"                      # simple column reference
  - expression: "DATE_TRUNC('month', sale_date)"  # raw DuckDB SQL
    alias: "sale_month"                     # required when using expression
```

### `order_by` — `direction`

Applies to both the task-level `order_by` and to `order_by` within `first`/`last` aggregations.

| `direction` | Meaning |
|-------------|---------|
| `asc` | Ascending — smallest / earliest value first |
| `desc` | Descending — largest / latest value first |

### `limit`

| Value | Behaviour |
|-------|-----------|
| `null` | No limit — all rows are included in the output |
| integer (e.g. `100`) | Output is capped at this many rows, after `order_by` is applied |

---

## Task type: `column_transformation`

Applies per-column transforms to an existing dataset and optionally appends new derived columns. Mirrors the standalone transformation config (see the Transformation Config Writing Guide for full details on each transform type). The keys available here are identical.

```yaml
- task_id: "enrich_summary"
  type: "column_transformation"

  source:
    file_id: "sales_summary_raw"

  columns:                    # optional — per-column transforms on existing columns
    - name: total_revenue
      transformations:
        - type: rename
          to: revenue_total
        - type: round
          decimal_places: 2

    - name: category
      transformations:
        - type: trim
          side: both
        - type: case_conversion
          to: upper
        - type: null_handling
          strategy: replace
          replace_with: "UNKNOWN"

  new_columns:                # optional — derived columns appended to the output
    - name: revenue_per_unit
      type: float
      value: expression
      expression: "ROUND(revenue_total / NULLIF(total_quantity, 0), 2)"

    - name: revenue_tier
      type: string
      value: conditional
      cases:
        - when: "revenue_total >= 50000"
          then: "High"
        - when: "revenue_total >= 10000"
          then: "Medium"
      else: "Low"

    - name: record_id
      type: string
      value: uuid

    - name: row_num
      type: integer
      value: series
      start: 1
      step: 1

    - name: loaded_at
      type: datetime
      value: expression
      expression: "NOW()"

  drop_columns: ["min_revenue"]    # optional — columns to remove from the output

  select_columns:                  # optional — final column order; omit to keep all
    - "category"
    - "sale_month"
    - "revenue_total"
    - "record_id"
    - "loaded_at"

  destination:
    file_id: "sales_summary_enriched"
```

### Supported `columns` transform types

| `type` | Key parameters |
|--------|---------------|
| `trim` | `side: both\|left\|right` |
| `cast` | `to: string\|integer\|float\|boolean\|date\|datetime` |
| `round` | `decimal_places: N` |
| `date_conversion` | `source_formats[]`, `target_format` |
| `substring` | `mode: position` → `start`, `length` |
| `substring` | `mode: pattern` → `pattern` |
| `regex_replace` | `pattern`, `replacement`, `flags` (default `'g'`) |
| `regex_validate` | `pattern`, `on_mismatch: nullify\|drop_row` |
| `case_conversion` | `to: upper\|lower` |
| `remove_non_printable` | `replace_with` (optional, default `""`) |
| `null_handling` | `strategy: replace` → `replace_with`, `include_empty` (opt) |
| `null_handling` | `strategy: drop_row`, `include_empty` (opt) |
| `concat` | `separator`, `parts[]` (`column` or `literal`) |
| `rename` | `to: <new_name>` |

### Supported `new_columns` value strategies

| `value` | Key parameters |
|---------|---------------|
| `fixed` | `fixed_value` |
| `expression` | `expression` (raw DuckDB SQL) |
| `arithmetic` | `expression` (raw DuckDB SQL) |
| `concat` | `separator`, `parts[]` |
| `conditional` | `cases[]` (`when`/`then`), `else` |
| `uuid` | _(none)_ |
| `series` | `start` (default 1), `step` (default 1) |
| `date_function` | `function: year\|month\|day\|day_of_week`, `source_column` |

> See the [Transformation Config Writing Guide](../transformations/config-writing-guide.md) for full parameter details and DuckDB equivalents of every type above.

---

## Task type: `validation`

Runs assertions against a dataset. On success, it is a pass-through — the `destination.file_id` is the same as the `source.file_id`. On failure, behaviour is controlled per assertion via `on_fail`.

```yaml
- task_id: "validate_sales_summary"
  type: "validation"

  source:
    file_id: "sales_summary_enriched"

  assertions:
    - check: "row_count"
      operator: "greater_than"    # greater_than | less_than | equal | between
      value: 0
      on_fail: "error"            # error | warn | skip

    - check: "not_null"
      columns: ["category", "revenue_total"]
      on_fail: "error"

    - check: "unique"
      columns: ["category", "sale_month"]   # uniqueness checked across all listed columns together
      on_fail: "warn"

    - check: "expression"
      expression: "revenue_total >= 0"
      description: "Revenue should never be negative"
      on_fail: "error"

  destination:
    file_id: "sales_summary_enriched"  # pass-through; same ID as source
```

### Assertion types

| `check` | Parameters | Description |
|---------|------------|-------------|
| `row_count` | `operator`, `value` | Checks total row count against a threshold |
| `not_null` | `columns[]` | Fails if any listed column contains a `NULL` |
| `unique` | `columns[]` | Fails if the combination of listed columns is not unique across all rows |
| `expression` | `expression`, `description` (opt) | Evaluates a DuckDB SQL `WHERE` expression; fails if any row does not satisfy it |

### `row_count` — `operator`

| `operator` | Assertion fails when row count… |
|------------|--------------------------------|
| `greater_than` | is **not** greater than `value` |
| `less_than` | is **not** less than `value` |
| `equal` | is **not** equal to `value` |
| `between` | falls outside the range `[value[0], value[1]]` (inclusive) |

### `on_fail` behaviour

| `on_fail` | Behaviour |
|-----------|-----------|
| `error` | Raise an exception, halt the pipeline |
| `warn` | Log a warning, continue |
| `skip` | Silently ignore the failure and continue |

---

## Fan-out pattern

When the same source is needed for multiple independent aggregations, list it as the `source.file_id` in multiple tasks. Tasks still run sequentially in order, but each reads independently from the same Parquet file — no duplication of data or config is needed.

```yaml
# Both tasks read from "merged_output" independently
- task_id: "agg_by_customer"
  type: "aggregation"
  source:
    file_id: "merged_output"    # ← shared
  group_by:
    - column: "customer_id"
  ...
  destination:
    file_id: "customer_agg"     # terminal ✓

- task_id: "agg_by_product"
  type: "aggregation"
  source:
    file_id: "merged_output"    # ← shared
  group_by:
    - column: "product_id"
  ...
  destination:
    file_id: "product_agg"      # terminal ✓
```

Both `customer_agg` and `product_agg` would be listed in `outputs`.

---

## Quick reference

### Top-level keys

| Key | Required | Description |
|-----|----------|-------------|
| `outputs` | yes | List of `{ file_id }` terminal destinations for `job.yml` |
| `tasks` | yes | Ordered list of task definitions |

### Task keys (all types)

| Key | Required | Description |
|-----|----------|-------------|
| `task_id` | yes | Unique identifier within this config |
| `type` | yes | `merge` \| `aggregation` \| `column_transformation` \| `validation` |
| `description` | no | Free-text label |
| `destination.file_id` | yes | Output identifier; referenced by downstream tasks or listed in `outputs` |

### `merge`-specific keys

| Key | Required | Description |
|-----|----------|-------------|
| `sources[].file_id` | yes | Source to include in the merge |
| `sources[].alias` | yes | Short name used in `joins` |
| `sources[].columns` | no | Column subset to select from the source |
| `sources[].prefix` | no | String prepended to ambiguous column names |
| `joins[].type` | yes | Join/union type |
| `joins[].left` / `right` | yes | Aliases of the two sides |
| `joins[].result_alias` | yes (for union) | Alias for the result, usable in later joins |
| `joins[].on` | yes (except cross/union) | List of `{ left_col, right_col, operator }` |
| `joins[].column_mapping` | no | Explicit column alignment for union types |
| `filters` | no | Row filter applied after all joins (same syntax as ingestion `filters`) |
| `deduplicate` | no | Deduplication after filters |

### `aggregation`-specific keys

| Key | Required | Description |
|-----|----------|-------------|
| `source.file_id` | yes | Input dataset |
| `group_by[]` | yes | `column` or `expression` + `alias` |
| `aggregations[]` | yes | `function`, `column`, `alias`, `order_by` (for `first`/`last`) |
| `having` | no | Post-aggregation row filter (same syntax as `filters`) |
| `order_by` | no | Output sort |
| `limit` | no | Cap output row count; `null` = no limit |

### `column_transformation`-specific keys

| Key | Required | Description |
|-----|----------|-------------|
| `source.file_id` | yes | Input dataset |
| `columns[]` | no | Per-column transform list |
| `new_columns[]` | no | Derived columns appended to the output |
| `drop_columns` | no | List of column names to remove |
| `select_columns` | no | Final column list and order; omit to keep all |

### `validation`-specific keys

| Key | Required | Description |
|-----|----------|-------------|
| `source.file_id` | yes | Input dataset |
| `assertions[]` | yes | List of `{ check, on_fail, … }` |
| `destination.file_id` | yes | Must equal `source.file_id` (pass-through) |
