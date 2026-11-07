# Phase 2: CLI Core Completion - Context

**Gathered:** 2026-04-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Complete missing CLI commands for document retrieval and collection management. This phase delivers:
- `multi-get` — batch document retrieval by glob, comma-separated IDs, or docid
- `ls` — list indexed documents as a virtual file tree
- `collection update-cmd` — set/clear a pre-index shell command per collection
- `collection include/exclude` — control collection participation in default queries
- `pull` — download and verify local GGUF model files
- `--line-numbers` — display line numbers in search and retrieval output

</domain>

<decisions>
## Implementation Decisions

### multi-get Interface
- **D-01:** `multi-get` accepts a single positional argument with auto-detection:
  - If the argument contains commas → split into a list of docids
  - If the argument contains glob wildcards (`*`, `?`) → treat as a glob pattern against indexed document paths
  - Otherwise → treat as a single docid or path

### ls Command Design
- **D-02:** Create a new **top-level** `docsift ls [collection] [subpath]` command that queries the database and displays indexed documents as a virtual file tree.
- **D-03:** The existing `collection ls` command remains unchanged; it continues to show filesystem scan results (what *would* be indexed).

### update-cmd Behavior
- **D-04:** The pre-index shell command is stored on the `Collection` model (new `pre_update_cmd` field) and persisted in the database.
- **D-05:** The command executes automatically before each `docsift index update <collection>`.
- **D-06:** If the command fails (non-zero exit code), the update stops immediately (fail fast). A clear error message is shown to the user.

### include/exclude Semantics
- **D-07:** `collection include <name>` and `collection exclude <name>` are aliases for `collection enable <name>` and `collection disable <name>`.
- **D-08:** All four commands toggle the existing `include_by_default` boolean on the `Collection` model. No new database fields are required.

### pull Command
- **D-09:** `pull` downloads GGUF model files to a local cache directory (default: `~/.docsift/models/`).
- **D-10:** Primary download source is HuggingFace Hub. ModelScope is supported as a fallback/alternative source for users in regions with limited HuggingFace access.
- **D-11:** The command verifies the downloaded file exists and is non-empty. Full checksum verification is nice-to-have but not required for this phase.

### line-numbers Output
- **D-12:** `--line-numbers` is supported on `get`, `multi-get`, and `search`/`query`/`vsearch` commands.
- **D-13:** In rich table output, line numbers are prepended to content snippets. In structured formats (JSON, CSV, MD, XML), line numbers are included as a separate `line_numbers` or `lines` field alongside content.

### Claude's Discretion
- Specific error message wording for update-cmd failures
- Exact virtual tree rendering style for `ls`
- Pull command progress reporting format
- line-numbers field naming in structured output formats

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & Roadmap
- `.planning/REQUIREMENTS.md` § CLI Completion — CLI-01 through CLI-05, CLI-08
- `.planning/ROADMAP.md` § Phase 2: CLI Core Completion — goal and success criteria

### CLI Reference & Documentation
- `docs/cli-reference.md` — expected command signatures and behavior for `multi-get`, `ls`, `pull`, and `collection` subcommands

### Existing Code (Patterns to Follow)
- `src/docsift/cli/main.py` — CLI entry point and global option handling
- `src/docsift/cli/commands/get.py` — existing `get` and stub `multi-get` commands
- `src/docsift/cli/commands/collection.py` — existing collection management commands (`enable`, `disable`, `ls`, etc.)
- `src/docsift/cli/commands/search.py` — search commands with output format flags
- `src/docsift/cli/commands/index.py` — `index update` command where update-cmd hook must integrate
- `src/docsift/cli/formatters.py` — output formatting utilities (JSON, CSV, MD, XML, table)
- `src/docsift/core/models.py` — `Collection`, `Document`, `SearchResult` data models
- `src/docsift/database/repositories.py` — `CollectionRepository`, `DocumentRepository`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `OutputFormatter` class in `formatters.py` already handles table, json, csv, md, xml, and files output. Extend it for line-number-aware formatting.
- `Tree` from `rich.tree` is already used in `collection ls` for filesystem trees — reuse for the indexed-document `ls` command.
- `CollectionRepository` has `get_by_name`, `list_all`, and `update` methods — sufficient for adding `pre_update_cmd` support.
- `DocumentRepository` has `list_by_collection` and `get_by_path` — enough for `ls` and `multi-get` implementations.

### Established Patterns
- CLI commands get `index_path` from `ctx.obj`, create a `Database`, and use `db.transaction()` or `db.connection` for repository access.
- User-facing errors raise `click.ClickException(str(e))`.
- Collection subcommands live in `src/docsift/cli/commands/collection.py` and are registered via `@click.group("collection")`.
- Top-level commands are registered directly on the main `cli` group in `main.py`.

### Integration Points
- `docsift index update` in `src/docsift/cli/commands/index.py` is where the `update-cmd` hook must be injected before scanning files.
- `src/docsift/cli/commands/get.py` is where `multi-get` currently lives as a stub — expand it in place.
- `src/docsift/cli/commands/search.py` needs `--line-numbers` added to `search`, `vsearch`, and `query` commands.

</code_context>

<specifics>
## Specific Ideas

- `multi-get` auto-detection should be generous: if the argument looks like a list (contains `,`) or a glob (contains `*` or `?`), handle it accordingly; otherwise fall back to single-item retrieval.
- `ls` should feel like `tree` output: collection name as root, directories as branches, documents as leaves.
- `update-cmd` examples from qmd workflows: `git pull`, `rsync -a remote:notes/ local/notes/` — commands that prepare the collection path before indexing.
- `pull` should accept a model identifier like `owner/repo/model.gguf` or a direct URL.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 02-cli-core-completion*
*Context gathered: 2026-04-15*
