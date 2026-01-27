# JSONL Snapshot Format

TaskTree snapshots use JSON Lines (JSONL): one JSON object per line.

## Record Types

Each line includes a `record_type` field. Supported values are:

- `meta`
- `feature`
- `task`
- `dependency`

## Serialization Settings

Snapshots are written with deterministic JSON settings:

- `sort_keys=True`
- `separators=(',', ':')`
- `ensure_ascii=False`

## Deterministic Ordering

Records appear in a fixed order to keep snapshots stable across runs:

1. `meta`
2. `feature`
3. `task`
4. `dependency`

Within each record type, ordering follows the snapshot view sort keys.
