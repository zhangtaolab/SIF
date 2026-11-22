---
phase: quick-261122-leb
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - docs/machine-migration.md
  - mkdocs.yml
  - tests/test_docs.py
autonomous: true
requirements: [QUICK-MACHINE-MIGRATION-GUIDE]
estimate:
  tokens: 30000
  raw_tokens: 30000
  tasks: 2
  confidence: low

must_haves:
  truths:
    - "A reader on machine A can inventory the installation (`sif --version`, `sif status`, `sif models status --json`, `sif collection list --verbose`), quiesce every writer (`sif watch --stop`, `sif watch --uninstall-service` if installed, `sif mcp daemon --stop`), and produce a verified snapshot with `sif index backup --output` — while knowing exactly which sidecars (`<db>.lock`, `<db>.watch.pid`, `<db>.mcp.pid`, `<db>-wal`, `<db>-shm`) must never travel."
    - "A reader on machine B can install the same or newer SIF, place the backup at the target DB path (there is no restore command), preserve the embedder identity (`SIF_MODEL_NAME`, `SIF_MODEL_TYPE`, `SIF_EMBEDDING_DIM`, `SIF_API_BASE`), copy or rebuild both caches, and verify the restored index with `sif status`, `sif collection list --verbose`, `sif models status --json`, and the three search subcommands."
    - "The guide explains source-path handling (same absolute layout is a no-op for `sif index update`; moved roots use `sif collection remove` + `sif collection add` + `sif index update` + `sif index embed`; a same-OS prefix rewrite is documented as advanced, and cross-OS rewrites are called unsafe), identity failure modes (dimension mismatch fails on open; same-width mismatch warns and is fixed with `sif index embed --force`), and platform limits (macOS↔Linux portable, Windows degradation-only)."
    - "The guide recreates the non-database state: `.env` in the invocation directory, `SIF_*` variables, `SIF_API_KEY` from a secret store, MCP client entries (stdio and HTTP), and watch service/daemon setup; it notes that per-collection `pre_update_cmd` strings travel in the DB but the commands must exist on machine B."
    - "The new page is listed in the mkdocs `nav` and in `tests/test_docs.py` `DOCS_FILES`, so `pytest tests/test_docs.py` validates its shell commands, JSON/SQL/Python blocks, and doc-content rules against the live CLI."
  artifacts:
    - "docs/machine-migration.md — new English guide with the migration procedure, tables, command examples, and troubleshooting"
    - "mkdocs.yml — `Machine Migration: machine-migration.md` added under the User Guide section"
    - 'tests/test_docs.py — `Path("docs/machine-migration.md")` added to DOCS_FILES'
  key_links:
    - "docs/machine-migration.md -> tests/test_docs.py DOCS_FILES: every fenced block and every `sif` shell line in the guide is validated against the live Click tree"
    - "docs/machine-migration.md -> mkdocs.yml nav: the page is discoverable in the published documentation"
    - "guide commands -> src/sif/cli: commands must exist at this HEAD, including `sif index backup`, `sif models status --json`, `sif watch --stop`, `sif mcp daemon --stop`, and `sif collection list --verbose`"
---

<objective>
Add a machine-to-machine migration guide at `docs/machine-migration.md` and register it in the documentation site and the docs test suite.

The guide turns the installed on-disk state into a repeatable move: which files carry the index, embedding cache, model cache, configuration, and integrations; how to quiesce writers and take a WAL-safe verified backup; which sidecars must never be copied; how to restore on machine B without a restore command; how to keep the embedder identity and source-path assumptions intact; and how to verify the restored index with the shipped CLI. It also records the supported route for moved notes and the identity failure modes, so the page is a decision aid, not just a copy list.

Purpose: give users a single, accurate runbook for moving a real SIF installation between machines without a full re-index or silent vector corruption.
Output: one new documentation page, one mkdocs nav entry, and one DOCS_FILES entry. No source or test-logic changes.

Scope boundaries (locked):
- Documentation only: do not change any file under `src/` or add a test function; `tests/test_docs.py` gets only the DOCS_FILES entry.
- Do not edit the generator-owned `docs/cli-reference.md` or `docs/configuration.md`; reference them instead.
- Add no dependencies and no new CLI surface.
- Only document commands that exist at this HEAD; do not invent a restore command, an export/import command, or a Windows daemon service.
- Do not describe Windows as fully supported: v1.2 is degradation-only (no detached watch, no `--install-service`, no POSIX index locking).
- Do not tell users to copy the database sidecars; the guide must name them as things that never travel.
- English prose, consistent with `docs/`.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@mkdocs.yml
@tests/test_docs.py
@docs/models.md
@docs/mcp-server.md
@docs/installation.md

Planning-time observations (verified 2026-11-22, HEAD 70e8df8, clean tracked tree with pre-existing untracked `.planning/` files):

- `docs/machine-migration.md` does not exist. `mkdocs.yml` has no migration entry at all: `nav` lists User Guide as CLI Reference then Search Algorithms. `tests/test_docs.py` `DOCS_FILES` has 12 entries including `docs/migration.md` (the DocSift→SIF rename guide), and `docs/migration.md` is itself not in `nav`.
- Docs CI (`.github/workflows/docs.yml`) runs `pytest tests/test_docs.py -v --no-cov`, then runs `python scripts/generate_cli_ref.py` and `python scripts/generate_config_ref.py` and requires `git diff --exit-code docs/cli-reference.md docs/configuration.md`. Baseline at planning time: `pytest tests/test_docs.py -q --no-cov` → 21 passed in 2.44s; `git diff --exit-code docs/cli-reference.md docs/configuration.md` → exit 0; `ruff check src tests` and `ruff format --check src tests` → both exit 0. `STATE.md` records the full suite at 3,234 passed / 1 skipped / 95.03% coverage at the v1.2 close, so the full-suite gate is 0 failed / 0 errors with coverage at or above `fail_under = 90`.
- `tests/test_docs.py` constraints that apply to every DOCS_FILES page: every `sif ...` line in a bash/shell/sh/zsh block is resolved with `--help` against the live Click tree; `test_no_bare_search_command` rejects a line matching `sif search` unless followed by `search`, `query`, or `vsearch`; `test_no_removed_commands_in_docs` rejects the literal strings for `sif collection create`, `sif collection add-path`, `sif search similar`, `sif mcp start`, `sif mcp config`, `sif query `, `sif embed `, and `sif vsearch `; JSON blocks must parse; SQL blocks must start with CREATE/SELECT/INSERT/UPDATE/DELETE/ALTER/DROP; `test_no_positional_args_for_option_only_commands` rejects a line starting with `sif status ` followed by a bare positional; `collection delete` is forbidden (use `collection remove`).
- Path/config facts: `Settings.get_db_path()` returns `SIF_DB_PATH` when set, else platformdirs `user_data_dir("sif")/sif.db` (macOS `~/Library/Application Support/sif/sif.db`, Linux `~/.local/share/sif/sif.db`). `Settings.get_cache_dir()` returns `SIF_CACHE_DIR` when set, else platformdirs `user_cache_dir("sif")` (macOS `~/Library/Caches/sif`, Linux `~/.cache/sif`). Settings reads `.env` from the invocation working directory (`env_file=".env"`, no path override).
- Backup facts (`src/sif/cli/commands/index.py`, `src/sif/database/maintenance.py`): `sif index backup [--output PATH]` requires an existing index, takes the index lock, uses the SQLite online backup API, refuses an existing target, refuses a symlink/WAL/SHM/lock collision and stale target sidecars, runs `PRAGMA integrity_check` and only then reports success, chmods the copy 0600. Default output is `<db_dir>/backups/<stem>-<UTC>.db`. There is no restore command.
- Sidecars: `<db_path>.lock` (index lock), `<db>.watch.pid` (watch daemon), `<db>.mcp.pid` (MCP daemon), `<db>-wal` and `<db>-shm` (WAL artifacts).
- Identity facts: the DB stores `index_meta['embedder.identity']` and the vec0 table width as `FLOAT[n]`. Opening with a different resolved dimension raises the schema dimension-mismatch error even for read-only commands; same width with a different model/pooling/prompts produces an identity mismatch warning; `sif index embed --force` re-embeds and certifies the new identity. `sif models status [--json]` reports `match` / `mismatch` / `dimension-mismatch` plus stored vs configured cache model ids.
- Cache facts: embedding cache is `<cache_dir>/embeddings_cache.db`, SQLite, keyed by `(content_hash, model_id)` where model_id is `model_type:model_name`, with `@api_base` when set (and prompt/revision suffixes when effective). Model cache is `<cache_dir>/models/<owner>/<name>` with `.sif-model.json`; `sif models status` states are absent/empty/unverified/legacy/valid; `sif models pull` is idempotent and does not pre-warm sentence-transformers models (their first load may download an HF snapshot into the SIF cache dir).
- CLI facts: `sif status` prints Index Path, Collections, Documents, Chunks, Contexts, Total Size, Watch, Vector lag. `sif collection list --verbose` prints each collection's absolute Path, Pattern, Documents, Chunks, Description. `sif watch --stop` / `sif watch --uninstall-service` / `sif mcp daemon --stop` exist. `sif search search`, `sif search query`, `sif search vsearch` are the three subcommands; `sif search search` accepts `--no-refresh`.
- Integration facts: MCP stdio is `sif mcp stdio`; HTTP is `sif mcp http --host 127.0.0.1 --port 8080` with `claude mcp add --transport http sif http://127.0.0.1:8080/mcp`; watch detach is `sif watch --detach`, service install is `sif watch --install-service`; per-collection `pre_update_cmd` is stored in the DB and set with `sif collection update-cmd <name> --cmd <command>`.
- Platform facts: macOS↔Linux DB is portable; GPU/device differences do not change stored vectors when model identity matches; Windows v1.2 is degradation-only (foreground watch/MCP/CLI work, detached watch/service/POSIX locking do not).
- Location differences are absolute-path differences: `collections.path`, `documents.path`, and `contexts.target_id` (`context_type='path'`) store absolute resolved paths. `sif index update` and the pre-search drift refresh skip a missing collection root with a warning and preserve documents; they never mass-delete.
</context>

<tasks>

<task type="auto">
  <name>Task 1: Write docs/machine-migration.md — the machine-to-machine migration runbook</name>
  <files>docs/machine-migration.md</files>
  <precondition>The checkout is at HEAD 70e8df8 with no `docs/machine-migration.md`; the guide documents only commands that exist in this tree. `pytest` and `ruff` are on PATH.</precondition>
  <action>
    Create `docs/machine-migration.md` in English. Use ATX headings, relative links to sibling docs, tables where the content is comparative, and fenced `bash` blocks for commands. The H1 title must be exactly `# Machine-to-Machine Migration`. Open with a short paragraph: this guide moves an existing SIF installation from machine A to machine B; SIF is local-first, so its state is on-disk files; the goal is to carry the index and caches instead of re-indexing; and link `migration.md` for the separate DocSift→SIF package rename.

    Use these H2 sections in this order and cover the facts listed under each.

    `## What Moves` — a table with State / Location / Transfer method rows for: index database; embedding cache; model cache; configuration; MCP and watch integrations; source notes. State that the index DB is self-contained (full document text, collections, documents, chunks, FTS5 tables and triggers, the vec0 `document_embeddings` table, contexts, query_log, llm_cache, and index_meta), so the original Markdown is not needed to serve search results, but the source roots are needed for `sif index update` and `sif watch`. Use `SIF_DB_PATH` else the platformdirs data dir (`~/Library/Application Support/sif/sif.db` on macOS, `~/.local/share/sif/sif.db` on Linux) for the DB, and `SIF_CACHE_DIR` else the platformdirs cache dir (`~/Library/Caches/sif` on macOS, `~/.cache/sif` on Linux) for the caches.

    `## Before You Start on Machine A` — bullets that tell the reader to record `sif --version`; `sif status` (Index Path); `sif models status --json` (`settings.model_name`, `settings.model_type`, `settings.api_base`, `settings.dimension`, `settings.cache_dir`, the cache state, and the identity status); `sif collection list --verbose` (absolute source paths, pattern, description); the `.env` file and every `SIF_*` variable; and the per-collection pre-update commands. State that `SIF_API_KEY` never appears in status output, so it must be recovered from the secret store. Then list the quiesce sequence: `sif watch --stop`; `sif watch --uninstall-service` if a service is installed; `sif mcp daemon --stop`; close any `sif mcp stdio`/`sif mcp http` clients and any running index/embed/search process; confirm `sif status` reports Watch not running. Name `<db>.watch.pid` and `<db>.mcp.pid` as the daemon PID artifacts.

    `## Export the Index from Machine A` — lead with `sif index backup --output /path/to/sif-backup.db` as the supported export. Explain that it requires an existing index, takes the cross-process index lock, uses the SQLite online backup API, refuses an existing target or a symlink/sidecar collision, verifies the copy with `PRAGMA integrity_check` before reporting success, and writes the copy mode 0600 because it contains full document text. Note the default output when `--output` is omitted is `<db_dir>/backups/<stem>-<UTC>.db`, and that the command prints Output and Size. Mention `sif index vacuum` as an optional pre-backup space reclaim that also requires no other writer, but not as a migration requirement. State plainly that there is no `sif index restore` command: restore means placing the backup file at the target DB path. If the reader chooses a raw file copy instead, require stopping all writers first and warn that copying only the bare `.db` while a writer is live can lose recent commits, which is why the backup command is preferred. Recommend an authenticated/encrypted transfer channel because the DB contains full text and absolute paths.

    `## Do Not Copy These Files` — name every sidecar and why: `<db>.lock` (cross-process index lock), `<db>.watch.pid` and `<db>.mcp.pid` (daemon identity/ownership), and `<db>-wal` / `<db>-shm` (live WAL state; copying them independently of a consistent snapshot can corrupt the copy or lose commits). Say the backup command folds WAL content into the single snapshot file and leaves no sidecars to copy. End with the positive list: the main DB (or the verified backup), `embeddings_cache.db`, the model cache tree, and the configuration files.

    `## Install SIF on Machine B` — install the same version as A or newer; schema migrations run automatically when the DB is opened, and older SIF than the schema is unsupported. Install the same extras/backends used on A (`embed`, `all`, `openai` as applicable) and link `installation.md`. State that `sqlite-vec` is a core dependency: BM25 search works without it, but CLI vector/hybrid paths fail fast and the MCP `hybrid_search` degrades to BM25 with a one-time warning. FTS5 ships with Python's SQLite. Confirm `sif --version` before restoring.

    `## Restore the Index on Machine B` — choose the target DB path (`SIF_DB_PATH` or the platform default), create the parent directory if needed, place the backup file there, keep it mode 0600, and ensure no stale `<db>.lock`, `<db>.watch.pid`, `<db>.mcp.pid`, `<db>-wal`, or `<db>-shm` sits beside it. Do not start watch or MCP before the identity check. Explain that `sif status` now opens the DB and prints Index Path and counts, and that the schema dimension guard runs even for read-only commands, so a model mismatch surfaces here. If restoring from a raw copy, repeat the consistent-snapshot and sidecar rules.

    `## Preserve the Embedder Identity` — explain that the DB records the embedder identity in `index_meta['embedder.identity']` and fixes the vector width as `FLOAT[n]`. Tell the reader to keep `SIF_MODEL_NAME`, `SIF_MODEL_TYPE`, `SIF_EMBEDDING_DIM`, and `SIF_API_BASE` identical to A, because the stored vectors and the embedding-cache key both depend on them. Different dimension: opening fails with the schema dimension-mismatch error even for read-only commands, so align the configuration or plan a rebuild. Same width but different model/pooling/prompts/revision: the open succeeds but emits an identity mismatch warning because the vectors are not comparable; run `sif index embed --force` to re-embed and certify the new identity. Note that GPU vs CPU/MPS does not change stored vectors when the identity matches. Point to `sif models status` and `sif models status --json` for match/mismatch/dimension-mismatch.

    `## Move or Rebuild the Caches` — embedding cache: copy `<cache_dir>/embeddings_cache.db` to the same location on B, or set `SIF_CACHE_DIR` to where it was copied. It is SQLite, keyed by `(content_hash, model_id)` with model_id `model_type:model_name` (plus `@api_base` when set and prompt/revision suffixes when effective), so it is portable when the model configuration matches; otherwise misses are harmless and B recomputes them. If omitted, B re-embeds on demand (slower, no data loss). Model cache: copy `<cache_dir>/models/<owner>/<name>` including `.sif-model.json`, or run `sif models pull` on B. List the cache states absent/empty/unverified/legacy/valid and say a valid entry requires the manifest plus every listed file to match size and SHA-256; `sif models pull` is idempotent and re-downloads an invalid entry. Note that `sif models pull` does not pre-warm sentence-transformers models: their first encode may download an HF snapshot into the SIF cache directory. Warn not to mix cache files from different model identities.

    `## Handle Source Paths` — state that `collections.path`, `documents.path`, and path-type `contexts.target_id` store absolute resolved paths. Same layout: keep the notes at the same absolute paths; after restore, `sif index update` should report unchanged. Notes moved on B: the supported route is `sif collection remove <name>`, then `sif collection add <new-root> --name <name>` (re-apply `--pattern`, repeated `--ignore`, `--description`, and `--no-default` as needed), then `sif collection update-cmd` for any pre-update command, `sif index update`, and `sif index embed`; the embedding cache makes re-embedding unchanged content cheap. Missing collection root: `sif index update` and the pre-search drift refresh warn and skip the missing root while preserving all indexed documents, never mass-deleting; `sif search search "..." --no-refresh` skips the pre-search walk when testing the restored index while sources are unavailable. Advanced same-OS prefix rewrite: stop every writer, take a backup, then in one transaction rewrite the `collections.path`, `documents.path`, and `contexts.target_id` prefixes for `context_type='path'`; the documents FTS triggers re-sync automatically; then `sif index update` should report unchanged. Include one fenced `sql` block with three parameterized `UPDATE` statements using `substr` and `:old_prefix`/`:new_prefix` (the docs test requires the first SQL keyword; `UPDATE` passes). State that this rewrite is safe only when the path layout and separator convention match (same OS) and that cross-OS rewrites are not safe: rebuild with remove/add/update/embed instead.

    `## Recreate Configuration and Integrations` — `.env` is read from the invocation working directory (`Settings` uses `env_file=".env"`, no path override), so recreate it there on B or export the `SIF_*` variables in the shell profile; `sif models status` shows the resolved settings. `SIF_API_KEY` comes from the secret store and is never printed by status; never commit `.env` or the DB backup, which contain user content and paths. MCP: stdio uses command `sif` with args `mcp stdio`; a Claude Desktop `mcpServers` entry carries `command` and `args`; HTTP uses `sif mcp http` (default `127.0.0.1:8080`) and the client command `claude mcp add --transport http sif http://127.0.0.1:8080/mcp`; the repo is also a Claude Code plugin. Link `mcp-server.md`. Watch: reinstall with `sif watch --detach` or `sif watch --install-service`; launchd/systemd definitions embed paths and flags, so they are recreated on B, not copied. Note that per-collection `pre_update_cmd` values travel in the DB but the commands must exist on B, and can be re-set with `sif collection update-cmd <name> --cmd <command>`. Add the Windows note: v1.2 Windows is degradation-only (no detached watch, no `--install-service`, no POSIX index locking); foreground watch/MCP/CLI work; prefer `SIF_DB_PATH` and confirm the resolved path with `sif status`.

    `## Verify the Migration` — a short ordered checklist: `sif --version`; `sif status` (Index Path, Collections/Documents/Chunks/Contexts match A, Watch not running until intentionally started, Vector lag); `sif collection list --verbose` (every path exists on B); `sif models status --json` (identity match, cache valid); `sif search search "..."` (BM25, no model load); `sif search query "..."` (hybrid); `sif search vsearch "..."` (vector); `sif index update` (should report unchanged when the source layout is the same). Start `sif watch` and the MCP client only after these checks pass.

    `## Troubleshooting` — a table with Symptom / Likely cause / Fix rows covering: dimension-mismatch error on every command; identity-mismatch warning; missing collection-root warning; `sif status` reporting no index or empty counts (wrong `SIF_DB_PATH`); watch/MCP refusing to start with a stale PID/lock artifact; `sif models status` reporting absent/empty/unverified/legacy; Windows refusing detach/service; and vector search finding nothing (vectors not restored or identity mismatch; check Vector lag and identity).

    `## Related Documentation` — relative links to `installation.md`, `configuration.md`, `models.md`, `mcp-server.md`, `cli-reference.md`, `architecture.md`, and `migration.md`.

    Documentation-test traps to respect while writing: every `sif search` occurrence must be followed by `search`, `query`, or `vsearch`; do not use the removed command spellings listed in the context; keep every JSON block valid JSON; every SQL block must start with a valid SQL keyword; write `sif status` as a standalone command with no bare positional argument; use `sif collection remove`, never a delete spelling. Do not edit any other file in this task.
  </action>
  <verify>
    <automated>
      ls docs/machine-migration.md 2>/dev/null | wc -l  # [HEAD=0 EXPECT==1]
      grep -c '^# Machine-to-Machine Migration$' docs/machine-migration.md  # [HEAD=error:2 EXPECT==1]
      grep -c '^## ' docs/machine-migration.md  # [HEAD=error:2 EXPECT>=13]
      grep -c '^## What Moves$' docs/machine-migration.md  # [HEAD=error:2 EXPECT==1]
      grep -c '^## Do Not Copy These Files$' docs/machine-migration.md  # [HEAD=error:2 EXPECT==1]
      grep -c '^## Preserve the Embedder Identity$' docs/machine-migration.md  # [HEAD=error:2 EXPECT==1]
      grep -c '^## Handle Source Paths$' docs/machine-migration.md  # [HEAD=error:2 EXPECT==1]
      grep -c '^## Troubleshooting$' docs/machine-migration.md  # [HEAD=error:2 EXPECT==1]
      grep -c 'sif index backup --output' docs/machine-migration.md  # [HEAD=error:2 EXPECT>=1]
      grep -c 'embeddings_cache.db' docs/machine-migration.md  # [HEAD=error:2 EXPECT>=1]
      grep -c '\.sif-model\.json' docs/machine-migration.md  # [HEAD=error:2 EXPECT>=1]
      grep -c 'sif mcp daemon --stop' docs/machine-migration.md  # [HEAD=error:2 EXPECT>=1]
      grep -c 'sif watch --uninstall-service' docs/machine-migration.md  # [HEAD=error:2 EXPECT>=1]
      grep -c 'sif collection list --verbose' docs/machine-migration.md  # [HEAD=error:2 EXPECT>=1]
      grep -c 'SIF_EMBEDDING_DIM' docs/machine-migration.md  # [HEAD=error:2 EXPECT>=1]
      grep -c 'sif search query' docs/machine-migration.md  # [HEAD=error:2 EXPECT>=1]
    </automated>
  </verify>
  <done>
    - `docs/machine-migration.md` exists with the exact H1 and all required H2 sections in the specified order
    - The guide names the supported backup command, both cache locations/manifests, all five sidecars to avoid, the identity variables, the three search subcommands, the watch/MCP stop commands, and the verification checklist
    - The guide covers same-layout, moved-root, and advanced same-OS prefix-rewrite paths for source notes, and calls cross-OS rewrites unsafe
    - The guide covers Windows degradation-only behavior and macOS↔Linux portability
    - No file other than `docs/machine-migration.md` was modified in this task
  </done>
</task>

<task type="auto">
  <name>Task 2: Register the guide in mkdocs nav and DOCS_FILES, then run docs validation and the quality suite</name>
  <files>mkdocs.yml, tests/test_docs.py, docs/machine-migration.md (fix-only if validation finds a guide violation)</files>
  <precondition>Task 1 created `docs/machine-migration.md`; `mkdocs.yml` and `tests/test_docs.py` still match HEAD 70e8df8; `pytest`, `ruff`, and `python` are on PATH.</precondition>
  <action>
    1. Edit `mkdocs.yml` with a scoped Edit (never a whole-file Write). In the `nav` list, under the existing `User Guide:` section, insert a third entry after `- Search Algorithms: search-algorithms.md`: `- Machine Migration: machine-migration.md`. Preserve the two-space list indentation and leave every other nav entry unchanged.

    2. Edit `tests/test_docs.py` with a scoped Edit. In `DOCS_FILES`, add `Path("docs/machine-migration.md"),` immediately after the existing `Path("docs/migration.md"),` entry. Do not change `SKIP_COMMAND_PATTERNS`, `JSON_OUTPUT_SCHEMAS`, any test body, or any other list.

    3. Run the docs validation exactly as CI does: `pytest tests/test_docs.py -q --no-cov`. The expected result is 21 passed, unchanged from the planning baseline, because DOCS_FILES expands coverage within the existing tests rather than adding a test. If a test fails on `docs/machine-migration.md`, fix only the guide: replace a bare search command with one of the three subcommands, remove a removed-command spelling, correct an invalid JSON/SQL block, or make `sif status` standalone. Never loosen a test assertion and never edit another doc to satisfy the failure.

    4. Run the generator no-diff gate: `python scripts/generate_cli_ref.py`, then `python scripts/generate_config_ref.py`, then `git diff --exit-code docs/cli-reference.md docs/configuration.md`. Both generated docs must be byte-identical to HEAD. If a generator rewrites them for a reason unrelated to this plan, restore them with `git checkout -- docs/cli-reference.md docs/configuration.md` and record the event in the SUMMARY; never hand-edit generated docs.

    5. Run `ruff check src tests` and `ruff format --check src tests`. The only Python edit is the one-line DOCS_FILES addition; both gates must pass with no formatter rewrite. If `ruff format --check` flags `tests/test_docs.py`, run `ruff format tests/test_docs.py` and note it.

    6. Run the full suite with the coverage gate active: `pytest -q`. Per `pyproject.toml`, `addopts` already enables `--cov=src/sif` with `fail_under = 90`. Require 0 failed and 0 errors; record the exact summary line and coverage percentage in the SUMMARY. Do not weaken the coverage gate.

    7. Scope audit: run `git status --porcelain` and confirm the only modified tracked files are `docs/machine-migration.md`, `mkdocs.yml`, and `tests/test_docs.py`, plus the pre-existing untracked `.planning/` artifacts. Confirm `src/`, `README.md`, other `docs/*.md`, `docs/cli-reference.md`, `docs/configuration.md`, and `.github/` are unmodified. Do not commit or push; leave commit handling to the execution workflow.
  </action>
  <verify>
    <automated>
      grep -c '^    - Machine Migration: machine-migration.md$' mkdocs.yml  # [HEAD=0 EXPECT==1]
      grep -c 'Path("docs/machine-migration.md"),' tests/test_docs.py  # [HEAD=0 EXPECT==1]
      pytest tests/test_docs.py -q --no-cov  # [HEAD=21 EXPECT==21 GUARD MUTATION: a violating fenced block or sif command in docs/machine-migration.md]
      python scripts/generate_cli_ref.py
      python scripts/generate_config_ref.py
      git diff --exit-code docs/cli-reference.md docs/configuration.md  # [HEAD=0 EXPECT==0 GUARD MUTATION: a CLI/config change without regenerating the generator-owned docs]
      ruff check src tests  # [HEAD=0 EXPECT==0 GUARD MUTATION: an unformatted or lint-violating Python edit]
      ruff format --check src tests  # [HEAD=0 EXPECT==0 GUARD MUTATION: a Python edit that needs reformatting]
      pytest -q  # [HEAD=0 EXPECT==0 GUARD MUTATION: a change that breaks any test or the 90% coverage gate]
    </automated>
  </verify>
  <done>
    - `mkdocs.yml` contains exactly one `- Machine Migration: machine-migration.md` entry under User Guide, with all other nav entries unchanged
    - `tests/test_docs.py` DOCS_FILES contains exactly one `Path("docs/machine-migration.md")` entry, with no test-logic change
    - `pytest tests/test_docs.py -q --no-cov` reports 21 passed, 0 failed; any failure was fixed in the guide, not in the tests
    - `git diff --exit-code docs/cli-reference.md docs/configuration.md` exits 0 after both generator scripts run, proving the generator-owned docs are untouched
    - `ruff check src tests` and `ruff format --check src tests` pass
    - Full `pytest -q` reports 0 failed / 0 errors with coverage at or above the 90% gate, and the exact summary line plus coverage percentage is recorded in the SUMMARY
    - `git status --porcelain` shows only the three planned files plus the pre-existing untracked `.planning/` artifacts; no source, README, other-docs, generated-docs, workflow, commit, or push change occurred
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| machine A disk -> transfer channel -> machine B disk | The index DB contains full document text and absolute paths; `.env` may contain `SIF_API_KEY`; a careless transfer discloses personal data or credentials |
| guide reader -> live index | Copying a bare `.db` while a writer is live, or copying `-wal`/`-shm` independently, can lose commits or corrupt the restored index |
| configured embedder -> stored vectors | A changed model identity or dimension makes restored vectors unusable or silently non-comparable |
| guide -> user's shell | Every documented command is executed by users; a nonexistent or destructive command damages trust and data |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-leb-01 | Information Disclosure | backup file, embedding cache, model cache, `.env`, API keys | medium | mitigate | Recommend an authenticated/encrypted transfer channel; state that the verified backup is chmod 0600 because it contains full document text; state that `SIF_API_KEY` is never printed by status and must come from the secret store; warn against committing `.env` or the backup. |
| T-leb-02 | Tampering (data integrity) | index database copy and sidecars | high | mitigate | Make `sif index backup` the supported export (online backup API, index lock, `PRAGMA integrity_check`, 0600) and explicitly list `<db>.lock`, `<db>.watch.pid`, `<db>.mcp.pid`, `<db>-wal`, and `<db>-shm` as files that must never travel; require writers to be stopped before any raw copy. |
| T-leb-03 | Tampering / Spoofing (vector identity) | restored vec0 table and embedder identity | high | mitigate | Require `SIF_MODEL_NAME`, `SIF_MODEL_TYPE`, `SIF_EMBEDDING_DIM`, and `SIF_API_BASE` to match machine A; document the dimension-mismatch open failure and the same-width mismatch warning; prescribe `sif index embed --force` for an accepted model change; point to `sif models status` for verification. |
| T-leb-04 | Repudiation | Windows capability claims | low | mitigate | State the v1.2 Windows degradation boundary explicitly and never advertise detached watch, `--install-service`, or POSIX locking on Windows. |
| T-leb-05 | Tampering / Denial of Service | documented commands | low | mitigate | Validate every `sif` command line through `tests/test_docs.py` against the live Click tree; document no restore, export, or import command that does not exist. |
| T-leb-SC | Tampering | npm/pip/cargo installs | low | accept | This plan installs nothing and adds no dependency; the guide only points readers at the existing PyPI installation procedure documented in `docs/installation.md`. |
</threat_model>

<verification>
1. Task 1: `docs/machine-migration.md` exists with the exact title, the required section order, and all required command/path tokens; no other file changed.
2. Task 2: `mkdocs.yml` has one Machine Migration nav entry and `tests/test_docs.py` has one new DOCS_FILES entry, with no test-logic edits.
3. Task 2: `pytest tests/test_docs.py -q --no-cov` is green (21 passed), proving every fenced block and every `sif` command in the new page passes the docs rules against the live CLI.
4. Task 2: both generator scripts run with `git diff --exit-code docs/cli-reference.md docs/configuration.md` returning 0.
5. Task 2: `ruff check src tests` and `ruff format --check src tests` pass.
6. Task 2: full `pytest -q` reports 0 failed / 0 errors with coverage at or above 90%.
7. Scope: `git status --porcelain` shows only the three planned files plus the pre-existing untracked `.planning/` artifacts; `src/`, `README.md`, other docs, generated docs, and workflows are untouched.
</verification>

<success_criteria>
- A user can move a real SIF installation from machine A to machine B by following one page: inventory, quiesce, verified backup, transfer, install, restore, identity/cache handling, integration recreation, and verification.
- The guide is accurate against the shipped CLI: `sif index backup`, `sif status`, `sif models status`, `sif collection list --verbose`, `sif watch --stop`, `sif watch --uninstall-service`, `sif mcp daemon --stop`, and the three `sif search` subcommands all exist and behave as described.
- The guide is discoverable through the mkdocs nav and enforced by `tests/test_docs.py`, with no source, generated-doc, dependency, workflow, commit, or push change.
</success_criteria>

<output>
Create `.planning/quick/261122-leb-write-a-machine-to-machine-migration-gui/261122-leb-SUMMARY.md` when done
</output>
