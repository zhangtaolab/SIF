
## Deferred Items

- ~~`sif search search <term> --json` emits raw control characters (literal newlines) inside the `snippet` field, so strict JSON parsers reject the output (`json.loads` needs `strict=False`). Pre-existing snippet serialization quirk discovered during 05-09 live verification; unrelated to context add/prune changes.~~
  **Status:** resolved
  Resolved 2026-09-10 — root cause was Rich `console.print` word-wrapping the JSON string at terminal width (not the data itself); fixed by quick task 260910-kps (commits `2f7cbb4`, `4d4bb02`): all machine-format branches (`--json`/`--csv`/`--md`/`--xml`/`--files` in search/vsearch/query, `--json` in bench) now emit via `click.echo`, with regression tests under forced `COLUMNS=80`.
