# Machine-to-Machine Migration

This guide moves an existing SIF installation from machine A to machine B. SIF
is local-first: its state is a handful of on-disk files, so a migration carries
the index and caches instead of re-indexing your corpus. Follow it top to
bottom — inventory and quiesce machine A, take a verified backup, install and
restore on machine B, then verify the result with the shipped CLI.

Looking for the DocSift to SIF package rename instead? That is a different
process, documented in [Migration Guide: DocSift to SIF](migration.md).

## What Moves

| State | Location | Transfer method |
|---|---|---|
| Index database | `SIF_DB_PATH` if set, else the platform data dir: `~/Library/Application Support/sif/sif.db` (macOS), `~/.local/share/sif/sif.db` (Linux) | `sif index backup --output`, then copy the single verified snapshot file |
| Embedding cache | `<cache>/embeddings_cache.db`, where `<cache>` is `SIF_CACHE_DIR` if set, else the platform cache dir: `~/Library/Caches/sif` (macOS), `~/.cache/sif` (Linux) | Copy the file (optional, but recommended) |
| Model cache | `<cache>/models/<owner>/<name>` under the same `<cache>` root | Copy the tree, or run `sif models pull` on machine B |
| Configuration | `.env` in the directory you invoke `sif` from, plus `SIF_*` variables in your shell profile | Recreate by hand; never bulk-copy secrets |
| MCP and watch integrations | MCP client entries, launchd/systemd service definitions | Recreate on machine B; service definitions embed absolute paths, and client entries must find the installed `sif` command |
| Source notes | Wherever your Markdown lives | Any file transfer (rsync, scp, git) |

The index database is self-contained. It holds the full document text, the
collection/document/chunk records, the FTS5 tables and their sync triggers,
the vec0 `document_embeddings` vector table, path contexts, the query log, the
LLM cache, and the index metadata (including the embedder identity). Search
works without the original Markdown. The source roots are still required for
`sif index update` and `sif watch`, and path contexts attach by path, so a
faithful migration keeps the notes available at the same paths.

## Before You Start on Machine A

Record the installation so machine B can be checked against it later:

```bash
# Version — machine B must run the same version or newer
sif --version

# Where the index lives and how large it is (note the Index Path row)
sif status

# Configured model identity, cache state, backend availability
sif models status --json

# Absolute source roots, patterns, and descriptions
sif collection list --verbose
```

From the JSON payload, record the `settings` section — `model_name`,
`model_type`, `api_base`, `dimension`, and `cache_dir` — plus the cache
`state` and the `identity` status. A healthy machine A looks like this (your
paths and revision differ):

```json
{
  "settings": {
    "model_name": "Qwen/Qwen3-Embedding-0.6B",
    "model_type": "modelscope",
    "api_base": null,
    "dimension": 1024,
    "cache_dir": "/Users/you/Library/Caches/sif/models"
  },
  "cache": {
    "path": "/Users/you/Library/Caches/sif/models/Qwen/Qwen3-Embedding-0.6B",
    "revision": "master",
    "state": "valid"
  },
  "backend": {
    "available": true,
    "name": "modelscope",
    "version": "1.36.0"
  },
  "vector_backend": {
    "available": true,
    "name": "sqlite_vec",
    "version": "0.1.9"
  },
  "identity": {
    "status": "match",
    "source": "verified",
    "stored_model_name": "Qwen/Qwen3-Embedding-0.6B",
    "stored_cache_model_id": "modelscope:Qwen/Qwen3-Embedding-0.6B",
    "stored_dimension": 1024,
    "stored_fingerprint": "sha256:654cea77113ea0ce",
    "schema_dimension": 1024,
    "current_cache_model_id": "modelscope:Qwen/Qwen3-Embedding-0.6B",
    "current_fingerprint": "sha256:654cea77113ea0ce"
  }
}
```

The stored and current fingerprints can differ while `status` is `match`:
identity comparison is field-wise, not fingerprint equality.

Also record:

- The `.env` file in the directory you invoke `sif` from (Settings reads
  `env_file=".env"` with no path override), and every `SIF_*` variable set in
  your shell profile.
- Any per-collection pre-update commands you configured with
  `sif collection update-cmd`. The command strings travel inside the database,
  but the programs they invoke must exist on machine B.
- `SIF_API_KEY` is never printed by status output. Recover it from your secret
  store — it cannot be recovered from the machine A files you are copying.

### Quiesce every writer

A consistent copy requires no active writer. Stop them in this order:

```bash
# Stop the detached watch daemon, if it is running
sif watch --stop

# Remove the OS service definition, if you installed one
sif watch --uninstall-service

# Stop the detached MCP daemon, if it is running
sif mcp daemon --stop
```

Then close anything that keeps a server busy: MCP stdio sessions
(`sif mcp stdio`), MCP HTTP clients, and any running `sif index update`,
`sif index embed`, or long-running search process. Confirm the quiet state:

```bash
sif status
```

The `Watch` row should report the daemon as not running. The daemon artifacts
are `<db>.watch.pid` and `<db>.mcp.pid` beside the database; once the
processes are stopped they are stale files and must never travel (see
[Do Not Copy These Files](#do-not-copy-these-files)).

## Export the Index from Machine A

The supported export is the backup command:

```bash
# Writes a verified single-file snapshot
sif index backup --output /path/to/sif-backup.db
```

The command:

- Requires an existing index — there is nothing to back up otherwise.
- Waits for the cross-process index lock (up to `SIF_LOCK_WAIT_TIMEOUT`,
  30 seconds by default) before copying; SQLite's online backup API keeps the
  snapshot consistent even if another writer starts afterwards.
- Uses the SQLite online backup API, folding WAL content into the single
  snapshot file.
- Refuses an existing target, and refuses a target path that collides with a
  symlink, a WAL/SHM file, a lock file, or stale target sidecars.
- Verifies the copy with `PRAGMA integrity_check` before reporting success.
- Writes the copy mode 0600 — it contains your full document text.

With `--output` omitted, the snapshot lands in
`<db_dir>/backups/<stem>-<UTC>.db`. Either way the command prints the
`Output` path and `Size` — record them. If disk space is tight, run
`sif index vacuum` when no other writer is active; it reclaims unused space.
It is optional and not part of the migration.

**There is no `sif index restore` command.** Restoring means placing the
backup file at the target database path on machine B (see
[Restore the Index on Machine B](#restore-the-index-on-machine-b)).

If you choose a raw file copy of the database instead, stop every writer
first — and know the risk: copying only the bare `.db` while a writer is live
can lose recent commits that were still sitting in the WAL. That is why the
backup command is preferred: it produces one verified file with no sidecar
ambiguity.

Transfer the snapshot over a channel you authenticate or encrypt (scp over
SSH, an encrypted archive). The file contains your full document text and the
absolute paths of your notes.

## Do Not Copy These Files

Never copy these files from machine A to machine B:

| File | What it is | Why it must not travel |
|---|---|---|
| `<db>.lock` | Cross-process index lock | Kernel lock state does not survive a copy, so the file is meaningless on machine B — leave it behind rather than ship a misleading artifact |
| `<db>.watch.pid` | Watch daemon PID artifact | The recorded PID may belong to an unrelated process on machine B; daemon ownership does not transfer |
| `<db>.mcp.pid` | MCP daemon PID artifact | Same — daemon ownership does not transfer |
| `<db>-wal` | Write-ahead log | Live WAL state; copying it independently of a consistent snapshot can corrupt the copy or lose commits |
| `<db>-shm` | WAL shared-memory file | Same — it is only meaningful alongside a live WAL |

The backup command folds the WAL into the single snapshot file and leaves no
sidecars to copy — one more reason to prefer it over a raw copy.

What does travel:

- The main database, or preferably the verified backup file.
- `embeddings_cache.db` (optional but recommended).
- The model cache tree (`<cache>/models/...`).
- The configuration files — the `.env` contents, recreated by hand.

## Install SIF on Machine B

Install the same version as machine A, or newer. Schema migrations run
automatically when the restored database is opened; an older SIF than the
schema on disk is unsupported. Follow [Installation](installation.md) and pick
the same extras you had on machine A — `embed` for local vector search, `all`
for GGUF and OpenAI-compatible backends, `openai` for API-only backends:

```bash
# Linux with an NVIDIA GPU — uv selects the CUDA build for the driver
uv tool install --torch-backend=auto 'docsif[embed]'
```

Two storage engines are worth knowing about:

- **FTS5** ships with standard Python's SQLite — nothing extra to install (if
  a custom build lacks it, use a Python whose SQLite includes FTS5).
- **sqlite-vec** is a core dependency. BM25 keyword search works without it,
  but the CLI vector and hybrid commands fail fast, and the MCP
  `hybrid_search` tool degrades to BM25-only with a one-time warning.

Confirm before restoring:

```bash
sif --version
```

macOS and Linux installations are mutually portable: the database and both
caches carry no platform-specific state, and GPU versus CPU versus MPS device
differences do not change stored vectors when the model identity matches (see
[Preserve the Embedder Identity](#preserve-the-embedder-identity)).

## Restore the Index on Machine B

Choose the target database path — set `SIF_DB_PATH`, or use the platform
default from [What Moves](#what-moves) — and place the backup there:

```bash
# Explicit target (recommended); unset to use the platform default
export SIF_DB_PATH=/path/to/sif.db
mkdir -p "$(dirname "$SIF_DB_PATH")"
mv /path/to/sif-backup.db "$SIF_DB_PATH"
chmod 600 "$SIF_DB_PATH"
```

Before the first open, make sure no stale artifacts sit beside the target:
`<db>.lock`, `<db>.watch.pid`, `<db>.mcp.pid`, `<db>-wal`, `<db>-shm`. A
directory that never held a SIF database has none; a reused directory might.

Do not start `sif watch` or an MCP server yet — the identity check comes
first.

Opening the index happens on the next command:

```bash
sif status
```

This opens the restored database, prints the `Index Path` and the
collection/document/chunk/context counts, and reports `Watch` as not running.
The schema dimension guard runs on every open — including read-only commands
like this one — so a model mismatch surfaces here rather than silently (see
[Preserve the Embedder Identity](#preserve-the-embedder-identity)).

If you restored from a raw file copy instead of the backup command, apply the
same rules that command enforces: the copy must have been taken with all
writers stopped, and none of the sidecar files may have traveled with it.

## Preserve the Embedder Identity

The database records the embedder identity in `index_meta['embedder.identity']`
and fixes the vector width in the schema as `FLOAT[n]`. Both the stored vectors
and the embedding-cache keys depend on that identity, so machine B must
resolve the identical embedder configuration:

- `SIF_MODEL_NAME` — the model id (for example `Qwen/Qwen3-Embedding-0.6B`)
- `SIF_MODEL_TYPE` — the backend (`modelscope`, `sentence_transformers`,
  `gguf`, `openai`)
- `SIF_EMBEDDING_DIM` — the embedding dimension
- `SIF_API_BASE` — the API base, when a remote backend is configured
- `SIF_QUERY_PROMPT_NAME` / `SIF_DOCUMENT_PROMPT_NAME` — only when you
  overrode the backend's default prompt scheme

Keep the other embedding settings (`SIF_MAX_TOKENS`, chunking settings)
identical as well: they are not part of the identity check, but they change
what text is embedded, so a silent difference produces different vectors on
future writes.

Failure modes:

- **Different dimension**: opening the database fails with the schema
  dimension-mismatch error — even for read-only commands. Align the
  configuration with machine A, or plan a rebuild from scratch.
- **Same width, different model/pooling/prompts/revision**: the database
  opens, but commands emit an identity mismatch warning, because vectors from
  the old model are not comparable with new query vectors. If you accept the
  new model, run `sif index embed --force` once to re-embed everything and
  certify the new identity.

Check the resolved state at any time:

```bash
sif models status --json
```

The `identity.status` field reports `match`, `mismatch`,
`dimension-mismatch`, or `no-index`/`no-identity` before vectors exist. GPU
versus CPU versus MPS does not require a re-embed — the stored vectors are
copied as-is, and minor floating-point differences across backends do not
change the vector space — only the model identity matters.

## Move or Rebuild the Caches

### Embedding cache

Copy `embeddings_cache.db` from the machine A cache root to the same location
in the machine B cache root, or set `SIF_CACHE_DIR` to wherever you copied it.
Copy it after the [quiesce step](#quiesce-every-writer); if a writer was still
active, take a consistent copy with SQLite's online backup API instead of a
plain file copy:

```bash
sqlite3 <cache>/embeddings_cache.db ".backup '/path/to/embeddings_cache.db'"
```

The cache is a SQLite database keyed by `(content_hash, model_id)`, where
`model_id` is `model_type:model_name` — plus `@api_base` when set, and
prompt/revision suffixes when they are in effect. It is portable when the
model configuration matches machine A; when it does not, entries simply miss
and machine B recomputes them — harmless, just slower.

If you skip the cache, nothing is lost: machine B re-embeds on demand, at the
cost of time.

Do not mix cache files from different model identities — the keys embed the
model id, but keeping one cache per identity avoids any ambiguity.

### Model cache

Either copy the model cache tree — `<cache>/models/<owner>/<name>`, including
the `.sif-model.json` manifest — or download again on machine B:

```bash
# Idempotent: a valid cache entry returns without network access
sif models pull
```

`sif models status` reports the cache state:

| State | Meaning |
|---|---|
| `absent` | No directory exists for the model |
| `empty` | A directory exists but holds no files |
| `unverified` | Files exist but `.sif-model.json` is missing or does not match |
| `legacy` | A recognized legacy layout holds the model; a pull migrates it |
| `valid` | The manifest and every listed file match size and SHA-256 |

A `valid` entry requires the manifest plus every listed file to match size and
SHA-256 — a partial copy reports `unverified`, and `sif models pull`
re-downloads it. The pull is idempotent. It does not pre-warm
sentence-transformers models: their first encode may still download a
Hugging Face snapshot into the SIF cache directory, so plan network access for
the first embedding run on machine B.

If machine A used `model_type=sentence_transformers`, its weights live in the
Hugging Face cache rooted at the SIF cache directory (`models--<owner>--<name>/`
and sibling `blobs/` entries), not under `<cache>/models`. Copy those
directories too, or let the first encode download them.

## Handle Source Paths

Absolute paths are stored in the database: `collections.path`,
`documents.path`, and path-type contexts in `contexts.target_id` (with
`context_type='path'`). How machine B's layout compares to machine A's decides
the route.

### Same layout

Keep the notes at the same absolute paths on machine B. After restoring:

```bash
sif index update
```

should report everything unchanged — the walk finds identical files with
identical checksums.

### Notes moved to a new root

The supported route is to re-register the collection at the new root and
re-index:

```bash
# Drop the old collection record (its document rows go with it)
sif collection remove notes

# Re-add at the new root; re-apply --pattern, --ignore (repeatable),
# --description, and --no-default as needed
sif collection add /new/notes --name notes --pattern '**/*.md'

# Re-set a pre-update command, if the collection had one
sif collection update-cmd notes --cmd 'make regenerate'

# Re-index from the new root; re-embed new paths
sif index update
sif index embed
```

The embedding cache keys on content hashes, not paths, so unchanged content
re-embeds from cache and only moved files cost new work.

### Missing collection root

If the notes are not available on machine B yet, nothing destructive happens:
`sif index update` and the pre-search drift refresh warn and skip the missing
root, preserving every indexed document — they never mass-delete. To test the
restored index while sources are unavailable, skip the pre-search walk:

```bash
sif search search "a phrase you know exists" --no-refresh
```

### Advanced: same-OS prefix rewrite

If the whole tree moved under a new prefix on the same OS (for example
`/data/notes` became `/srv/notes`), the stored paths can be rewritten in
place. Stop every writer, take a backup first, then run one transaction that
rewrites the three path-bearing columns:

```sql
-- Run inside ONE transaction after stopping every writer and taking a backup.
UPDATE collections
SET path = :new_prefix || substr(path, length(:old_prefix) + 1)
WHERE path LIKE :old_prefix || '%';
UPDATE documents
SET path = :new_prefix || substr(path, length(:old_prefix) + 1)
WHERE path LIKE :old_prefix || '%';
UPDATE contexts
SET target_id = :new_prefix || substr(target_id, length(:old_prefix) + 1)
WHERE context_type = 'path' AND target_id LIKE :old_prefix || '%';
```

The documents-side FTS triggers re-sync automatically as the `documents.path`
values change. Bind the two parameters before running the block — the `sqlite3`
shell accepts `.parameter set :old_prefix '/data/notes'` and `.parameter set
:new_prefix '/srv/notes'`; wrap the three statements in `BEGIN;` … `COMMIT;`.
Afterwards `sif index update` should report unchanged.

This rewrite is safe only when the path layout and separator convention match
— that is, machine B runs the same OS as machine A. Cross-OS rewrites are not
safe (path separators and normalization differ): use the remove/add/update/
embed route above instead.

## Recreate Configuration and Integrations

Settings reads `.env` from the invocation working directory
(`env_file=".env"`, no path override). Recreate the file in the directory you
invoke `sif` from on machine B, or export the `SIF_*` variables in your shell
profile. `sif models status` shows the resolved settings — compare them
against your machine A inventory.

`SIF_API_KEY` comes from your secret store; it is never printed by status
output. Never commit `.env` or the database backup — both contain user
content and absolute paths.

### MCP clients

stdio clients (Claude Desktop, the Claude Code plugin) launch `sif` as a
command:

```json
{
  "mcpServers": {
    "sif": {
      "command": "sif",
      "args": ["mcp", "stdio"]
    }
  }
}
```

HTTP clients connect to the Streamable HTTP server. Start it in the
foreground:

```bash
sif mcp http --host 127.0.0.1 --port 8080
```

and register it with Claude Code:

```bash
claude mcp add --transport http sif http://127.0.0.1:8080/mcp
```

The repository is also a Claude Code plugin and marketplace — see
[MCP Server](mcp-server.md) for the plugin, the daemon, and transport
security.

### Watch

Reinstall the watcher on machine B — launchd and systemd definitions embed
paths and flags, so they are recreated, not copied:

```bash
# Detached daemon
sif watch --detach

# Or the OS-supervised service (launchd on macOS, systemd on Linux)
sif watch --install-service
```

Per-collection `pre_update_cmd` values travel inside the database, but the
commands they name must exist on machine B. Re-set any of them with
`sif collection update-cmd <name> --cmd <command>`.

### Windows

Windows in v1.2 is degradation-only: foreground `sif watch`, MCP stdio and
HTTP, and the CLI work, but detached watch, `--install-service`, and POSIX
index locking are refused or degrade with a clear message. If machine B is
Windows, set `SIF_DB_PATH` explicitly and confirm the resolved location with
`sif status`.

## Verify the Migration

Run the checks in order and compare against your machine A inventory:

```bash
sif --version
sif status
sif collection list --verbose
sif models status --json
sif search search "a phrase you know exists"
sif search query "a topic you know exists"
sif search vsearch "a phrase with no exact keywords"
sif index update
```

- `sif status` — `Index Path` points at the restored file; the
  `Collections`/`Documents`/`Chunks`/`Contexts` counts match machine A;
  `Watch` is not running until you intentionally start it; `Vector lag` is 0.
- `sif collection list --verbose` — every collection's `Path` exists on
  machine B.
- `sif models status --json` — `identity.status` is `match` and the cache
  `state` is `valid`.
- `sif search search "..."` — BM25 works without loading a model.
- `sif search query "..."` — hybrid search works with the embedder.
- `sif search vsearch "..."` — vector search returns comparable results.
- `sif index update` — reports unchanged when the source layout is the same.

Start `sif watch` and your MCP clients only after these checks pass.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Dimension-mismatch error on every command, including read-only ones | `SIF_EMBEDDING_DIM` or `SIF_MODEL_NAME` resolves differently than the stored identity | Match machine A's settings, or rebuild the index from scratch |
| Identity mismatch warning on every open | Same width, different model, pooling, prompts, or revision | Accept the new model with `sif index embed --force`, or restore the old configuration |
| Missing collection root warning while indexing | Notes are not at the stored absolute paths on machine B | Move the notes to the recorded paths, or use the remove/add/update/embed route |
| `sif status` reports no index or empty counts | `SIF_DB_PATH` points somewhere other than the restored file | Set `SIF_DB_PATH` to the restored file and re-run |
| A stale `<db>.watch.pid`, `<db>.mcp.pid`, or `<db>.lock` sits beside the restored database | Copied from machine A | Stop any live process, then delete these artifacts; `sif status` cleans a stale watch PID on its own |
| `sif models status` reports absent, empty, unverified, or legacy | Model cache missing or partially copied | Run `sif models pull` to download or migrate |
| Windows refuses `--detach` or `--install-service` | v1.2 Windows is degradation-only | Run watch and MCP HTTP in the foreground |
| Vector search returns nothing while keyword search works | Vectors were not restored, or the identity changed | Check `Vector lag` in `sif status` and `identity.status` in `sif models status --json`; on a mismatch, re-embed with `--force` |

## Related Documentation

- [Installation](installation.md) — install methods, extras, and the
  degradation matrix
- [Configuration](configuration.md) — every `SIF_*` variable
- [Data Models](models.md) — the schema behind the index and the model cache
- [MCP Server](mcp-server.md) — client configuration, transports, and the
  plugin
- [CLI Reference](cli-reference.md) — every command and flag
- [Architecture](architecture.md) — how the index, FTS5, and vector tables fit
  together
- [Migration Guide: DocSift to SIF](migration.md) — the package rename,
  unrelated to machine moves
