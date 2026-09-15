---
status: diagnosed
phase: 06-documentation-audit-refresh
source: 06-01-SUMMARY.md, 06-02-SUMMARY.md, 06-03-SUMMARY.md, 06-04-SUMMARY.md, 06-05-SUMMARY.md, 06-06-SUMMARY.md, 06-07-SUMMARY.md
started: 2026-09-15T00:00:00Z
updated: 2026-09-15T00:30:00Z
verification_mode: agent-executed (user-delegated, session 2026-09-15)
---

## Current Test

[testing complete — 7/7 executed: 1 pass, 6 issues, 8 gaps diagnosed]

## Tests

### 1. CLI reference accuracy
expected: docs/cli-reference.md command tree and spot-checked options match the live CLI (`sif --help`, per-command `--help`)
result: issue
reported: |
  Command INVENTORY is complete and correct: all 32 leaf commands in docs/cli-reference.md match
  the live tree (`sif --help` + 6 group --helps: collection 11, context 5, get 2, index 3, mcp 3,
  search 3 + top-level bench/cleanup/ls/pull/status). But option-level drift is PROVEN by running
  `make docs-generate` and diffing (4 hunks, restored via git checkout afterward):
  (a) `search query`, `search search`, `search vsearch` options tables omit `-q, --quiet`
  (added post-phase-06 by quick task 260910-kps, commit 2f7cbb4; live --help shows it on all three);
  (b) `mcp http` omits `--cors-origins` (live `sif mcp http --help` lists it; added with phase-09
  CORS work — mcp-server.md:318 documents the CORS default that flag controls);
  (c) `index embed --chunk-strategy` typed `text` (cli-reference.md:386) vs live `choice`
  [auto|fixed|markdown|code] (converted to Click Choice in WR-06, commit bda12a2);
  (d) global `--config` default `/Users/forrest/.sif/config.yaml` (cli-reference.md:13) vs live
  DEFAULT_CONFIG_PATH `~/.config/sif` (src/sif/config/constants.py:13).
  Secondary (not gapped — regenerated output matches committed, so it is a shared generator
  format limitation, not drift): `collection add --name` is `[required]` in live help but the
  options table does not mark required options.
severity: major

### 2. Configuration reference accuracy
expected: docs/configuration.md defaults match live Settings.model_fields (Qwen/Qwen3-Embedding-0.6B, 1024 dim, Qwen3-Reranker-0.6B); validator rules section present; no phantom fields (no BM25 Settings / Configuration Profiles sections)
result: issue
reported: |
  Qwen3 model defaults, 1024 dim, chunking (512/128 = constants.py:16-17), mcp_port 8080, and the
  legacy phantom SECTIONS (BM25 Settings, Configuration Profiles) are all correct/absent as claimed.
  But three defaults/claims are stale vs live src/sif/config/settings.py:
  (a) `SIF_MODEL_TYPE` documented default `sentence_transformers` (configuration.md:59, .env example
  :130) vs live default `modelscope` (settings.py:61-64) — confirmed by docs-generate diff;
  (b) `SIF_RERANKER_MODEL_TYPE` documented default `transformers` (configuration.md:75, :135) vs live
  `sentence_transformers` (settings.py:90-93); "transformers" is not an accepted value —
  create_reranker (src/sif/search/rerank.py:391-427) raises `Unknown reranker model_type: transformers`
  unless the model name contains "qwen3-reranker" (auto-detection happens to mask it for the default
  model);
  (c) Validation Rules table and error example list `huggingface` as a valid model_type
  (configuration.md:113, :169) but the live validator explicitly rejects it (settings.py:161,
  valid_types = {sentence_transformers, gguf, openai, modelscope}; removed by WR-07, commit 60a2c08).
  Also phantom env var `SIF_ENV_FILE` (configuration.md:206) — pydantic-settings reads a hardcoded
  `.env` file; SIF_ENV_FILE is not honored.
severity: major

### 3. Quickstart command validity
expected: every command example in docs/quickstart.md exists in the live CLI (no collection create / add-path / search similar / mcp start / phantom env vars)
result: issue
reported: |
  All 31 unique `sif ...` command paths extracted from docs/quickstart.md resolve against the live
  CLI (verified via group/leaf --help): collection add/list/show/rename/remove/exclude/include,
  context add global/collection/path + list/remove, index update/embed (+--collection/--force),
  search search/vsearch/query (+--limit/-c/--all/--explain/--candidate-limit/--intent/--json/
  --md/--csv/--xml/--files), get get/multi-get, ls, status, cleanup, mcp stdio/http, --version.
  Env vars in the .env sample (SIF_DB_PATH/MODEL_NAME/EMBEDDING_DIM/CHUNK_SIZE/LOG_LEVEL) are all
  real Settings fields. No collection create / add-path / search similar / mcp start anywhere.
  One non-command defect: quickstart.md:359 `sif search query "python" --json | jq '.results[].
  .document_path'` references a JSON shape that does not exist — the CLI emits a top-level ARRAY
  (src/sif/cli/commands/search.py:44-48 json.dumps([r.to_dict(), ...])) with key `path`
  (SearchResult.to_dict, core/models.py:223-228). Correct filter: `jq '.[].path'`; the documented
  one silently returns nothing.
severity: minor

### 4. README + index accuracy
expected: README.md and docs/index.md state the correct default model and feature list without "planned" labels on implemented features (OpenAI API, query expansion, reranking, MCP server); install instructions work for the current distribution name
result: issue
reported: |
  docs/index.md fully accurate (commands, Qwen3 model mention, features, links). README accurate on
  default model (Qwen/Qwen3-Embedding-0.6B, README.md:173), feature list has no "planned" labels on
  implemented features, roadmap items are all genuinely unshipped from a user perspective (watcher.py
  exists but is not wired to any CLI/MCP surface). Install instructions coherent post-rename:
  `pip install sif` matches pyproject `name = "sif"` (renamed from docsif in 25fff2d), `pip install
  "sif[all]"` matches the existing `all` extra, `pipx install sif`, `pip install -e ".[dev]"` all
  valid. One stale flag: README.md:89 `sif collection remove old-collection --force` — live command
  has no `--force`; the confirmation skip flag is `--yes` (`sif collection remove --help`;
  cli-reference.md:201-205 documents --yes correctly).
severity: minor

### 5. Topic docs accuracy (post phases 7-9)
expected: docs/mcp-server.md documents actual commands (stdio/http/daemon); docs/models.md dataclass fields match src; docs/architecture.md module structure matches the CURRENT tree (e.g., unified src/sif/mcp/ — mcp_server/ was deleted in phase 9); search-algorithms.md class names exist
result: issue
reported: |
  search-algorithms.md: CLEAN — BM25Searcher, VectorSearcher, HybridSearcher, SearchPipeline,
  QueryExpansion, create_reranker, SmartSnippetExtractor all exist in src/sif/search/; usage examples
  match live signatures (BM25Searcher.search takes query:str, bm25.py:42); schema/FTS5/vec0 claims
  match src/sif/database/schema.py:200-223.
  mcp-server.md: mostly accurate for the unified package (MCPServer/SearchBackend/ToolHandler/
  StdioTransport/HTTPTransport match src/sif/mcp/{server,backend,handlers}.py + mcp/transports/;
  tools query/get/multi_get/status match handlers.py:45-198; updated post-09 at 28b20e9). Two stale
  spots: `daemon` subcommand undocumented (UAT expected stdio/http/daemon; only stdio+http at
  mcp-server.md:30-64), and SIF_DB_PATH default stated `~/.sif/index.sqlite` (mcp-server.md:185,:197)
  vs live computed `~/.local/share/sif/sif.db` (constants.py:11, settings.py:195-204).
  models.md: dataclass fields verified accurate (Collection core/models.py:34-49, SearchOptions
  :241-256, SearchResult :208-221, PathContext :183-192 all match); ONE stale default —
  EmbeddingConfig.model_type shown `SENTENCE_TRANSFORMERS` (models.md:283) vs live `MODELSCOPE`
  (src/sif/models/embedding.py:21).
  architecture.md: HEAVILY STALE (last content update was phase 06; only branding touched since at
  9a75979): documents `mcp_server/` directory tree (architecture.md:276-281) that phase 09 DELETED
  (`ls src/sif/mcp_server` → No such file); mislists `mcp/` as "Legacy functional" with files
  server_http.py/transport_stdio.py/transport_http.py/tools.py (:282-290) that do not exist, while
  omitting actual backend.py/handlers.py/transports/; Mermaid graph carries mcp_server node
  "(Refactored)" + mcp "(Legacy)" labels (:322-334) — inverted vs post-09 reality and stale vs its
  own "generated from actual source imports" claim (:348); module tree omits watcher.py,
  context_attach.py, term_match.py, progress.py, text.py, cache.py, embedder.py, models/download.py
  and lists nonexistent embedding/models.py; Factory "Supported Models" lists HuggingFace (:136)
  which raises NotImplementedError; indexing flow uses pre-phase-05 signature `sif collection add
  my-collection ~/notes` (:161) vs live `collection add PATH --name`; "Future Enhancements" lists
  incremental indexing and cross-encoder reranking (:514,:519) though both are implemented.
severity: major

### 6. Docs validator suite
expected: `pytest tests/test_docs.py` passes (part of the 675-green suite); validator covers the DOCS_FILES it claims (JSON blocks, command examples)
result: pass
reported: |
  `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/test_docs.py -v` → 12 passed in 1.80s
  (system/conda python 3.13.9, not uv venv). `make docs-test` → 12 passed. Validator covers the 9
  files it lists in DOCS_FILES (tests/test_docs.py:19-28): README.md, docs/index.md, cli-reference,
  configuration, quickstart, mcp-server, search-algorithms, architecture, models. Coverage
  observation (not gapped): api-reference.md, changelog.md, contributing.md, installation.md,
  migration.md and development.md (known-excluded) are outside DOCS_FILES. Note the validator checks
  command PATHS only, not flags — which is exactly how README's `--force` and cli-reference's missing
  `--quiet` pass through it.
severity: n/a

### 7. Docs tooling (Makefile + CI)
expected: `make docs-test` runs the docs validator; `make docs-generate` runs generate_cli_ref.py + generate_config_ref.py without error against live code; .github/workflows/docs.yml exists and is valid YAML
result: issue
reported: |
  Mechanics pass: `make docs-test` → 12 passed; `make docs-generate` → both scripts exit 0 against
  live code (imports updated to `sif` post-rename) and rewrote both files; docs.yml parses via
  yaml.safe_load. BUT the regeneration output FAILS the project's own validator: running
  `pytest tests/test_docs.py` against the regenerated docs → 3 failures (test_shell_commands_exist,
  test_no_bare_search_command, test_no_positional_args_for_option_only_commands). Root cause is in
  the generator scripts, not the live code: generate_config_ref.py:294-297 emits nonexistent
  `sif config show` / `sif config show --with-defaults` (phase 06-06 hand-fixed the committed doc to
  `sif status`; the generator would revert that fix), generate_cli_ref.py:260 emits positional
  `sif index update my-notes` (live requires `--collection`), :263 emits bare `sif search "python
  tips"` (search is a group). The generator also bakes the stale huggingface validation rows
  (generate_config_ref.py:192,:280) and phantom SIF_ENV_FILE (:343). CI never catches this because
  docs.yml runs docs-test on committed docs and gates generation drift with `git diff --exit-code
  ... || true` (non-blocking). Working tree restored with `git checkout -- docs/cli-reference.md
  docs/configuration.md` after evidence capture; nothing committed.
severity: major

## Summary

total: 7
passed: 1
issues: 6
pending: 0
skipped: 0

## Gaps

```yaml
- gap_id: G-06-1
  truth: "docs/cli-reference.md option tables match the live Click CLI params for every command"
  status: failed
  reason: >-
    docs-generate diff (restored after capture) proves drift: search query/search/vsearch tables
    (docs/cli-reference.md:434-450, 468-481, 499-508) omit -q/--quiet added in 2f7cbb4;
    mcp http table (:539-544) omits --cors-origins; index embed --chunk-strategy typed text not
    choice (:386, WR-06 bda12a2); global --config default /Users/forrest/.sif/config.yaml (:13)
    vs live ~/.config/sif (constants.py:13).
  severity: major
  test: 1
  root_cause: >-
    cli-reference.md last generated 2026-04-18; CLI flags added afterward (--quiet 2f7cbb4,
    --cors-origins phase 09, Choice-typed --chunk-strategy bda12a2) were never regenerated,
    and the generator bakes a user-specific --config default instead of constants.py's.
  artifacts:
    - path: docs/cli-reference.md
      issue: option tables stale vs live CLI
    - path: scripts/generate_cli_ref.py
      issue: hardcoded --config default; not re-run post-04-18
  missing:
    - "Regenerate/resync option tables; fix generator's --config default sourcing"
  debug_session: ""
- gap_id: G-06-2
  truth: "docs/configuration.md defaults and validation rules match live Settings (model_type=modelscope, reranker_model_type=sentence_transformers, huggingface rejected, no phantom env vars)"
  status: failed
  reason: >-
    SIF_MODEL_TYPE default documented sentence_transformers (configuration.md:59,:130) vs live
    modelscope (settings.py:61-64); SIF_RERANKER_MODEL_TYPE documented transformers (:75,:135) vs
    live sentence_transformers (settings.py:90-93) — transformers raises in create_reranker
    (rerank.py:424) for non-Qwen3 names; validation table + error example list huggingface as valid
    (:113,:169) but validator rejects it (settings.py:161, WR-07 60a2c08); phantom SIF_ENV_FILE
    (:206) is not honored by pydantic-settings.
  severity: major
  test: 2
  root_cause: >-
    configuration.md hand-written claims never re-synced after WR-07 moved model_type default to
    modelscope and removed huggingface from valid_types; SIF_ENV_FILE was documented speculatively.
  artifacts:
    - path: docs/configuration.md
      issue: stale defaults, invalid huggingface row, phantom SIF_ENV_FILE
    - path: src/sif/config/settings.py
      issue: source of truth (lines 61-161)
  missing:
    - "Sync defaults + validation table to settings.py; delete SIF_ENV_FILE row"
  debug_session: ""
- gap_id: G-06-3
  truth: "docs/quickstart.md JSON-piping example matches the CLI's actual --json output shape"
  status: failed
  reason: >-
    quickstart.md:359 uses jq '.results[].document_path' but the CLI emits a top-level array with
    key 'path' (search.py:44-48; SearchResult.to_dict core/models.py:223-228). Correct filter is
    jq '.[].path'; documented one silently returns nothing.
  severity: minor
  test: 3
  root_cause: >-
    jq filter written against an assumed {results:[...]} wrapper; actual --json emits a top-level
    array with path keys (search.py:44-48, core/models.py:223-228).
  artifacts:
    - path: docs/quickstart.md
      issue: ":359 jq filter targets nonexistent shape"
  missing:
    - "Change example to jq '.[].path'"
  debug_session: ""
- gap_id: G-06-4
  truth: "README.md example flags exist on the live CLI"
  status: failed
  reason: >-
    README.md:89 uses `sif collection remove old-collection --force`; live command has no --force
    — confirmation skip flag is --yes (sif collection remove --help; cli-reference.md:201-205).
  severity: minor
  test: 4
  root_cause: >-
    README example predates the collection remove flag surface; the confirmation-skip flag is
    --yes, no --force exists.
  artifacts:
    - path: README.md
      issue: ":89 uses nonexistent --force"
  missing:
    - "Replace --force with --yes"
  debug_session: ""
- gap_id: G-06-5
  truth: "docs/architecture.md module structure and diagrams match the current src/sif/ tree (unified mcp/, no mcp_server/)"
  status: failed
  reason: >-
    architecture.md:276-281 documents mcp_server/ deleted in phase 09 (ls src/sif/mcp_server fails);
    :282-290 lists mcp/ as 'Legacy functional' with nonexistent server_http.py/transport_stdio.py/
    transport_http.py/tools.py, omitting real backend.py/handlers.py/transports/; Mermaid graph
    (:322-334) keeps mcp_server '(Refactored)' node though :348 claims generation from live source;
    module tree omits watcher.py/context_attach.py/term_match.py/progress.py/text.py/cache.py/
    embedder.py and lists nonexistent embedding/models.py; :136 lists HuggingFace as a supported
    factory model though it raises NotImplementedError; :161 shows pre-phase-05 `collection add
    my-collection ~/notes` arg order; :514/:519 list incremental indexing and cross-encoder
    reranking as future though implemented.
  severity: major
  test: 5
  root_cause: >-
    architecture.md never revisited after phase 09 unified mcp/mcp_server (and phase 05 reordered
    collection add args); its hand-maintained module tree and Mermaid diagram drifted from the live
    tree, and its "generated from live source" claim (:348) was not re-run.
  artifacts:
    - path: docs/architecture.md
      issue: "documents deleted mcp_server/, phantom mcp/ files, stale arg order, wrong future list"
    - path: scripts/generate_arch_diagram.py
      issue: "not re-run since phase 06"
  missing:
    - "Rewrite module tree + Mermaid against live src/sif/; fix collection add arg order; drop HuggingFace factory row; move implemented items out of 'future'"
  debug_session: ""
- gap_id: G-06-6
  truth: "docs/models.md EmbeddingConfig default model_type matches src/sif/models/embedding.py"
  status: failed
  reason: >-
    models.md:283 shows model_type default ModelType.SENTENCE_TRANSFORMERS; live default is
    ModelType.MODELSCOPE (src/sif/models/embedding.py:21). All other dataclass field listings
    verified accurate.
  severity: minor
  test: 5
  root_cause: >-
    models.md default not updated when EmbeddingConfig.model_type default moved to MODELSCOPE
    (src/sif/models/embedding.py:21).
  artifacts:
    - path: docs/models.md
      issue: ":283 stale SENTENCE_TRANSFORMERS default"
  missing:
    - "Sync :283 default to ModelType.MODELSCOPE"
  debug_session: ""
- gap_id: G-06-7
  truth: "docs/mcp-server.md documents all three mcp subcommands and the real default db path"
  status: failed
  reason: >-
    daemon subcommand (live: sif mcp daemon) is undocumented — Transport Types section
    (mcp-server.md:30-64) covers stdio/http only; SIF_DB_PATH default stated ~/.sif/index.sqlite
    (mcp-server.md:185,:197) vs live computed ~/.local/share/sif/sif.db (constants.py:11,
    settings.py:195-204).
  severity: minor
  test: 5
  root_cause: >-
    mcp-server.md was updated at 28b20e9 (phase 09) but the daemon subcommand and the computed
    default db path were missed.
  artifacts:
    - path: docs/mcp-server.md
      issue: "daemon undocumented; ~/.sif/index.sqlite default wrong"
    - path: src/sif/config/constants.py
      issue: "source of truth (:11 computed ~/.local/share/sif/sif.db)"
  missing:
    - "Document sif mcp daemon; fix SIF_DB_PATH default to ~/.local/share/sif/sif.db"
  debug_session: ""
- gap_id: G-06-8
  truth: "make docs-generate produces docs that pass the project's own docs validator (make docs-test)"
  status: failed
  reason: >-
    Generator scripts emit invalid commands: generate_config_ref.py:294-297 emits nonexistent
    `sif config show [--with-defaults]`; generate_cli_ref.py:260 emits positional `sif index update
    my-notes` (live requires --collection); :263 emits bare `sif search "python tips"` (group, not
    leaf). Regenerating then running pytest tests/test_docs.py → 3 failures
    (test_shell_commands_exist, test_no_bare_search_command,
    test_no_positional_args_for_option_only_commands). Generator also bakes stale huggingface
    validation rows (:192,:280) and phantom SIF_ENV_FILE (:343), and would revert phase-06-06's
    hand fixes. CI masks this: docs.yml runs generation drift check with `|| true` (non-blocking)
    and docs-test only on committed docs.
  severity: major
  test: 7
  root_cause: >-
    Generator scripts were never updated after phase 06-06's hand fixes, so they emit nonexistent
    commands (sif config show, bare sif search, positional sif index update) and stale rows
    (huggingface, SIF_ENV_FILE); CI's generation drift check is non-blocking (|| true), so the
    regeneration loop rotted silently.
  artifacts:
    - path: scripts/generate_cli_ref.py
      issue: ":260,:263 invalid command examples"
    - path: scripts/generate_config_ref.py
      issue: ":192,:280,:294-297,:343 stale rows + nonexistent sif config show"
    - path: .github/workflows/docs.yml
      issue: "drift check runs with || true (non-blocking)"
  missing:
    - "Fix generator example commands and stale rows so regenerated docs pass tests/test_docs.py; consider making the CI drift check blocking"
  debug_session: ""
```

## Drift Summary

Phase 06 wrote these docs on 2026-04-18 against the then-current code; phases 03/04/05/08/09 and
quick tasks (260910-kps click.echo/--quiet, 260914-vyr distribution rename docsif→sif) landed
afterward. The command INVENTORY survived (renames were applied by 08-06/260914-vyr and the
validator enforces coverage), but option-level and backend-default detail drifted: the CLI gained
--quiet (search trio), --cors-origins (mcp http), Choice-typed --chunk-strategy; Settings'
model_type default moved to modelscope and huggingface became invalid (WR-07); mcp_server/ was
deleted and mcp/ unified (phase 09) leaving architecture.md describing a tree that no longer
exists. Separately, the two generator scripts were never updated after phase 06-06's hand fixes,
so the documented regeneration workflow now emits validator-failing output — meaning the docs
cannot be safely regenerated until the generators are fixed, which is why live-code drift
accumulated unchecked in the first place.
