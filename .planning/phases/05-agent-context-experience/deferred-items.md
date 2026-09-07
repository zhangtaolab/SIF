
## Deferred Items

- `sif search search <term> --json` emits raw control characters (literal newlines) inside the `snippet` field, so strict JSON parsers reject the output (`json.loads` needs `strict=False`). Pre-existing snippet serialization quirk discovered during 05-09 live verification; unrelated to context add/prune changes. status: open
