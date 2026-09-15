---
status: complete
phase: 07-cli-claude-skill
source: 07-01-SUMMARY.md, 07-02-SUMMARY.md
started: 2026-09-15T02:10:00Z
updated: 2026-09-15T07:30:00Z
verification_mode: agent-executed (user-delegated, session 2026-09-15)
---

## Current Test

[testing complete — 4/4 executed: 2 pass, 2 issues; both gaps G-07-1/G-07-2 resolved same session (symlinks restored, SKILL.md prose corrected)]

## Tests

### 1. Skill files exist and are well-formed
expected: both SKILL.md files exist in-repo with valid frontmatter (name/description) and structured guidance
result: pass
reported: |
  Both files present and well-formed. .claude/skills/sif-search/SKILL.md: frontmatter has name:
  sif-search, description ("Search documents in SIF index using BM25, vector, or hybrid search"),
  argument-hint, allowed-tools [Bash]; body is structured <objective>/<process>/<example> with
  numbered process steps. .claude/skills/sif-get/SKILL.md: name: sif-get, description ("Retrieve
  document content from SIF index by path, ID, or pattern"), same structure. Both carry the quick
  task 260914-wxv content (mtime 2026-09-14). Names match their directory names.
severity: n/a

### 2. Skill command examples valid against live CLI
expected: every `sif ...` invocation in both SKILL.md files resolves against the live CLI (search query/search/vsearch variants, get get/multi-get, flags like --json/--limit); no stale commands (the `sif update` hints were fixed by quick task 260914-wxv — verify clean)
result: pass
reported: |
  Extracted every `sif ...` invocation from both files (9 distinct forms in sif-search incl.
  examples; 6 in sif-get) and verified each against `python -m sif.cli.main --help` chain plus live
  runs against the real index (~/Library/Application Support/sif/sif.db, 1 collection / 2 docs):
  (a) global `-q/--quiet` before subcommand exists (top-level --help); (b) `search query`,
  `search search`, `search vsearch` all exist with `--json`, `--limit` (-n), `--line-numbers`,
  `-c/--collection`, `--all` (all three --helps); (c) `get get` takes PATH_OR_DOCID with
  `--line-numbers`, `--lines` (-l), `--from-line` (-f); `get multi-get` takes PATTERN with
  `--line-numbers` — comma-separated support confirmed in source (cli/commands/get.py:160-168) and
  live ("doc1.md,doc2.md" → 2 docs); glob "*.md" live → 2 docs; (d) error-hint command
  `sif index update` exists (index group: embed/status/update). Stale-pattern grep
  (`sif update` standalone, `sif collection create`, `sif index add`) → zero matches in both
  files — quick task 260914-wxv fix HOLDS. Live runs: `search query --json "SQLite FTS5"` →
  valid top-level JSON array with path/score/snippet/highlights keys; `search search --json` →
  valid; `search vsearch --json` resolves and runs (returns [] — this scratch index has 0 embedded
  chunks, environmental); `get get --line-numbers doc1.md` works (by filename). `sif` also
  installed in PATH at /Users/forrest/miniconda3/bin/sif v0.2.1, matching pyproject name = "sif".
severity: n/a

### 3. Symlinks live
expected: ~/.claude/skills/sif-search and ~/.claude/skills/sif-get are symlinks pointing at the repo skill dirs; Claude Code discovers them (they appear in the session's available skills)
result: issue
reported: |
  The claimed user-level symlinks DO NOT EXIST: `ls -la ~/.claude/skills/` shows no sif-search or
  sif-get entries. What remains are two STALE BROKEN symlinks from 2026-06-08 —
  docsift-get -> /Users/forrest/GitHub/docsift/.claude/skills/docsift-get and
  docsift-search -> /Users/forrest/GitHub/docsift/.claude/skills/docsift-search — whose target repo
  no longer exists (`ls /Users/forrest/GitHub/docsift` → No such file or directory), so they resolve
  to nothing and appear in no skill list. Both plan summaries list the user-level symlink as a
  deliverable ("~/.claude/skills/sif-search -> /Users/forrest/GitHub/SIF/.claude/skills/sif-search"),
  so the deliverable is absent from current state. Mitigation (why not fully broken): Claude Code
  discovers the skills from the PROJECT-level /Users/forrest/GitHub/SIF/.claude/skills/ directory —
  both sif-search and sif-get DO appear in this session's available-skills list and are invocable
  here. Net effect: skills work inside the SIF repo, but in any other Claude session the skills are
  unavailable, defeating the user-level availability the symlinks were created for.
severity: major

### 4. Skills describe current behavior
expected: skill guidance matches post-phase-9/quick-task reality — machine-format flags via click.echo, distribution name sif, correct db path defaults; no claims about removed/renamed commands
result: issue
reported: |
  The explicitly-scoped checks PASS: (a) --json output is clean machine format — live
  `sif -q search query --json` emits a valid top-level JSON array (quick task 260910-kps click.echo/
  no-wrap holds), fields path/score/snippet/highlights as the skill claims; empty result is `[]`
  exactly as the skill's "report No results found" step assumes; (b) distribution name: skills say
  "Requires sif CLI... in PATH" — pyproject name = "sif", installed `sif` v0.2.1 resolves; (c) no
  db-path or model-name claims in either skill, so nothing stale there; (d) no removed/renamed
  command references (no docsift, no `sif update`, correct `sif index update`). But two prose claims
  about output behavior do NOT match the live CLI: (1) sif-get objective says "first line is the
  path, followed by content" — live `sif -q get get` prints a 4-line header: title/filename first,
  then "Path: ...", then "Collection: ...", then a blank line, then content (cli/commands/get.py:
  85-88); a consumer expecting path-as-first-line misparses the header. (2) Both skills' error
  handling assumes non-zero exit + stderr ("If return code != 0: return stderr"; sif-search: "If
  stderr contains 'No index found'") — but on a missing index the CLI exits 0 and writes nothing to
  stderr: `get get` prints "No index found." to STDOUT (get.py:41-43), and `search` under the
  skills' mandatory `-q` is fully SILENT (search.py:141-144 guards the message with `if not quiet`;
  verified live with -i /tmp/nonexistent-sif.db: empty stdout+stderr, exit 0). An LLM following the
  skill gets an empty string with no error signal.
severity: minor

## Summary

total: 4
passed: 2
issues: 2
pending: 0
skipped: 0

## Gaps

```yaml
- gap_id: G-07-1
  resolved_by: orchestrator (symlink restoration, 2026-09-15)
  resolved_at: 2026-09-15
  truth: "~/.claude/skills/sif-search and ~/.claude/skills/sif-get are live symlinks to /Users/forrest/GitHub/SIF/.claude/skills/sif-{search,get}, and no stale docsift-* skill symlinks remain"
  status: resolved
  reason: >-
    User-level sif-* symlinks (a stated deliverable in 07-01-SUMMARY.md and 07-02-SUMMARY.md) do
    not exist in ~/.claude/skills/; instead two broken docsift-* symlinks dated 2026-06-08 remain,
    pointing at /Users/forrest/GitHub/docsift/.claude/skills/docsift-{get,search} — a repo path
    that no longer exists (repo renamed/moved to SIF in phase 08). Skills currently work only via
    project-level discovery inside /Users/forrest/GitHub/SIF; any other Claude session has no
    access to them.
  severity: major
  test: 3
  root_cause: >-
    When the repo moved from GitHub/docsift to GitHub/SIF the old user-level symlinks were never
    repointed/renamed to sif-*; the docsift-* links were left behind broken and the sif-* links
    claimed in the phase summaries were never (re-)created.
  artifacts:
    - path: "/Users/forrest/.claude/skills/docsift-search"
      issue: "broken symlink -> nonexistent /Users/forrest/GitHub/docsift/.claude/skills/docsift-search"
    - path: "/Users/forrest/.claude/skills/docsift-get"
      issue: "broken symlink -> nonexistent /Users/forrest/GitHub/docsift/.claude/skills/docsift-get"
    - path: "/Users/forrest/GitHub/SIF/.claude/skills/"
      issue: "target dirs exist and are healthy; only the user-level links are missing"
  missing:
    - "ln -s /Users/forrest/GitHub/SIF/.claude/skills/sif-search ~/.claude/skills/sif-search"
    - "ln -s /Users/forrest/GitHub/SIF/.claude/skills/sif-get ~/.claude/skills/sif-get"
    - "rm the two broken docsift-* symlinks"
  debug_session: ""
- gap_id: G-07-2
  resolved_by: orchestrator (SKILL.md prose fixes, 2026-09-15)
  resolved_at: 2026-09-15
  truth: "Skill prose describing non-JSON output and the missing-index error path matches live CLI behavior (get header layout; exit code and stream of 'No index found')"
  status: resolved
  reason: >-
    (a) sif-get SKILL.md objective claims "first line is the path, followed by content"; live
    `sif -q get get` prints title/filename, then "Path: ...", "Collection: ...", blank line, then
    content (cli/commands/get.py:85-88). (b) Both skills' error handling assumes non-zero exit +
    stderr for the missing-index case, but `get get` prints "No index found." to stdout with exit 0
    (get.py:41-43) and `search` under the skills' mandatory -q is completely silent with exit 0
    (search.py:141-144 guards the hint with `if not quiet`; verified live with
    -i /tmp/nonexistent-sif.db). All explicitly-scoped checks pass (click.echo --json output, top-
    level array with path/score/snippet/highlights, distribution name sif, no db-path/model claims,
    no stale commands), so this is prose-level only.
  severity: minor
  test: 4
  root_cause: >-
    Skill output-format/error-path prose was written against assumed CLI behavior in April and
    never re-verified: rich Console prints to stdout (not stderr), missing-index paths return exit
    0, and the get header block predates the description.
  artifacts:
    - path: ".claude/skills/sif-get/SKILL.md"
      issue: "objective 'first line is the path' vs live title/Path/Collection header block; error section assumes stderr/non-zero for missing index"
    - path: ".claude/skills/sif-search/SKILL.md"
      issue: "step 5 'If stderr contains No index found' — under -q the CLI emits nothing, exit 0"
    - path: "src/sif/cli/commands/get.py"
      issue: "source of truth (:41-43 missing-index stdout/exit 0; :85-88 header layout)"
    - path: "src/sif/cli/commands/search.py"
      issue: "source of truth (:141-144 missing-index hint suppressed under quiet)"
  missing:
    - "Fix sif-get objective to describe the actual title/Path/Collection header"
    - "Fix error-handling sections in both skills: missing index = empty output (search, under -q) or stdout message + exit 0 (get); suggest checking empty output, not stderr"
  debug_session: ""
```

## Drift Summary

Phase 07 (April) delivered two healthy in-repo SKILL.md files whose command surface has been kept
current — quick task 260914-wxv scrubbed the stale `sif update` hints and the `sif index update`
replacement is valid, and quick task 260910-kps's clean click.echo --json output matches the
skills' machine-format claims (verified live: top-level JSON array, `[]` on no match). What did
not survive is the environment half of the phase: the phase-08 repo rename from docsift to SIF
orphaned the user-level symlinks, leaving broken docsift-* links in ~/.claude/skills and no sif-*
links at all, so the skills are reachable only from sessions inside the SIF repo. Separately, the
skills' prose about non-JSON output shape and the missing-index error path (stderr + non-zero
exit) never matched the rich-console reality and now mildly misleads consumers.
