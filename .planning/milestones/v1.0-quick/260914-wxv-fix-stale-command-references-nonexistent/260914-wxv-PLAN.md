---
phase: 260914-wxv-fix-stale-command-references-nonexistent
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/sif/cli/main.py
  - src/sif/cli/commands/bench.py
  - src/sif/cli/commands/search.py
  - docs/development.md
  - .claude/skills/sif-search/SKILL.md
  - .claude/skills/sif-get/SKILL.md
autonomous: true
requirements: [DOC-02, DOC-04]
estimate:
  tokens: 18000
  raw_tokens: 18000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "Every 'No index found' hint in src/ that names a command now names only REAL commands: `sif index update` (main.py status, bench.py, search.py search/vsearch/query) and `sif index embed` (search.py vsearch, whose old hint also misnamed the embed step) — proven by live CLI runs against a nonexistent SIF_DB_PATH printing the corrected hints"
    - "docs/development.md 'Testing with Real Data' block (lines ~436-446) uses only real commands — `sif collection add ./test-data --name test`, `sif index update`, `sif index embed`, `sif search search \"test query\"` — and the debug block (~line 358) uses `sif search search \"query\"` (DOC-04)"
    - "Both live skills' error-handling notes (.claude/skills/sif-search/SKILL.md:66, .claude/skills/sif-get/SKILL.md:71) tell the user to run `sif index update` (DOC-02)"
    - "Negative grep gates return ZERO hits across src/, docs/, the two live skills, README.md, CLAUDE.md for the four stale patterns (nonexistent top-level update, collection-create, index-add, bare quoted search) — including one EXTRA stale site found by sweep beyond the audit: docs/development.md:358"
    - "Every distinct command named in corrected text is PROVEN to exist via `--help`: index update, index embed, collection add, search search (all pre-verified during planning; executor re-cites output)"
    - "`env -u FORCE_COLOR NO_COLOR=1 python -m pytest` is green at the 675-passed baseline (2 order-dependent caplog failures in tests/unit/embedding/test_openai_embedder.py are pre-existing per WINDOWS.md #3/#4 — confirm in isolation if they appear); `ruff check src tests` and `ruff format --check src tests` clean"
    - "No tests assert the old hint strings (verified during planning: grep of tests/ for the old hints returns nothing), so no test edits are required"
  artifacts:
    - "src/sif/cli/main.py — status hint names the real index-update command"
    - "src/sif/cli/commands/bench.py — bench hint names the real index-update command"
    - "src/sif/cli/commands/search.py — three hints (search/vsearch/query) name real commands; vsearch hint also names the real embed command"
    - "docs/development.md — two bash blocks contain only executable, real commands"
    - ".claude/skills/sif-search/SKILL.md and .claude/skills/sif-get/SKILL.md — error-handling notes name the real index-update command"
  key_links:
    - "src hint strings -> src/sif/cli/commands/index.py:44 update_cmd (`sif index update`) and index.py:234 embed_cmd (`sif index embed`)"
    - "docs/development.md collection example -> src/sif/cli/commands/collection.py:26 collection_add (usage: `sif collection add PATH --name NAME`, matches README.md:40 canonical form)"
    - "docs/development.md search examples -> src/sif/cli/commands/search.py:104 search_cmd (`sif search search QUERY`)"
    - "skill notes -> same index-group commands the CLI hints now use (consistency across all user-facing surfaces)"
---

<objective>
Eliminate every user-facing reference to nonexistent SIF CLI commands (v1.0 milestone audit DOC-02/DOC-04, integration Finding 7). The CLI's "No index found" hints tell users to run a top-level update command that does not exist; one hint also misnames the embed command. docs/development.md's "Testing with Real Data" and debug blocks show three command forms that do not exist. Both live Claude skills carry the same nonexistent-command note in their error handling.

Purpose: users (and agents following the skills) who hit "No index found" are currently directed into dead ends; v1.0 must not ship hints that cannot be executed.
Output: 6 files edited (string-only in src/), zero stale command references remaining, full suite green.

Verified command surface (planner-proven this session via `--help` and source read — executor re-cites):
- `sif index update` (index.py:44), `sif index embed` (index.py:234), `sif index status` (index.py:411)
- `sif collection add PATH --name NAME` (collection.py:26; also remove/rename/list/show/enable/disable/update-cmd/include/exclude/ls) — NOTE: path is the positional ARG, name is a required `--name` OPTION
- `sif search search|vsearch|query QUERY` (search.py:104/256/387)
- There is NO top-level update or embed command; there is no bare `sif search <query>`.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@CLAUDE.md

Source of truth for command existence (read once, do not re-derive):
@src/sif/cli/commands/index.py
@src/sif/cli/commands/collection.py
@src/sif/cli/commands/search.py

Facts established during planning (trust these):
- The five src hint sites are the ONLY src occurrences: main.py:107, bench.py:64, search.py:145, search.py:294, search.py:447. collection.py:137 prints a plain "No index found." with no command — leave untouched.
- search.py:294 names TWO bad commands: the nonexistent top-level update AND a nonexistent top-level embed. Both need correcting to the index-group forms.
- tests/test_docs.py does NOT validate docs/development.md (DOCS_FILES at tests/test_docs.py:19-30 omits it — this is WHY the stale examples survived the Phase 06 validator). Do NOT add development.md to DOCS_FILES in this task; that risks cascading new validator failures from other pre-existing development.md content and is out of scope.
- No tests anywhere assert the old hint strings (grep of tests/ is clean) — zero test edits expected.
- ~/.claude/skills/docsift-get and docsift-search are symlinks into /Users/forrest/GitHub/docsift/ — a DIFFERENT repo, not these files. Do NOT touch them.
- Global `-q` flag exists (main.py:49), and `sif get get` / `sif get multi-get` exist — the skills' other command forms are valid and need no changes.
- Canonical collection-add phrasing to mirror: README.md:40 `sif collection add ~/Documents/notes --name my-notes`.
</context>

<tasks>

<task type="auto">
  <name>Task 1: Correct the five CLI "No index found" hint strings in src/ (DOC-02)</name>
  <files>src/sif/cli/main.py, src/sif/cli/commands/bench.py, src/sif/cli/commands/search.py</files>
  <action>String-literal-only edits; no logic changes. Find each site with `grep -n "No index found" src/sif/cli/` and correct ONLY the command names inside the quoted suggestions at these five lines, per the verified command surface:
  - src/sif/cli/main.py:107 (status command): the suggestion to create an index must name the index-group update command — final text reads `No index found. Run 'sif index update' to create one.` (running that command with zero collections creates the DB file and then itself points to `sif collection add`, which already exists as a correct hint at index.py:71 — the onboarding chain stays coherent).
  - src/sif/cli/commands/bench.py:64: final text reads `No index found. Run 'sif index update' first.`
  - src/sif/cli/commands/search.py:145 (BM25 subcommand): same form as bench.py — `sif index update` first.
  - src/sif/cli/commands/search.py:294 (vsearch subcommand, multi-line console.print): BOTH commands in the suggestion are wrong — the real forms are the index-group update and the index-group embed. Final text reads `No index found. Run 'sif index update' and 'sif index embed' first.`
  - src/sif/cli/commands/search.py:447 (hybrid query subcommand): same form as bench.py.
  Do NOT touch the plain no-command "No index found." message in collection.py (or any similar bare message elsewhere); do NOT reformat surrounding code; keep Rich markup tags (`[yellow]...[/yellow]`) exactly as they are.
  </action>
  <verify>
    <automated>cd /Users/forrest/GitHub/SIF && ! grep -rn "sif update\|sif embed " src/ && grep -c "Run 'sif index update'" src/sif/cli/main.py src/sif/cli/commands/bench.py src/sif/cli/commands/search.py | awk -F: '{s+=$2} END {exit (s==5)?0:1}' && env -u FORCE_COLOR NO_COLOR=1 SIF_DB_PATH=/tmp/260914-wxv-none.db python -m sif.cli.main status 2>&1 | grep -F "Run 'sif index update' to create one." && env -u FORCE_COLOR NO_COLOR=1 SIF_DB_PATH=/tmp/260914-wxv-none.db python -m sif.cli.main search search x 2>&1 | grep -F "Run 'sif index update' first." && env -u FORCE_COLOR NO_COLOR=1 SIF_DB_PATH=/tmp/260914-wxv-none.db python -m sif.cli.main search vsearch x 2>&1 | grep -F "and 'sif index embed' first." && env -u FORCE_COLOR NO_COLOR=1 SIF_DB_PATH=/tmp/260914-wxv-none.db python -m sif.cli.main search query x 2>&1 | grep -F "Run 'sif index update' first." && env -u FORCE_COLOR NO_COLOR=1 SIF_DB_PATH=/tmp/260914-wxv-none.db python -m sif.cli.main bench --fixture /dev/null 2>&1 | grep -F "Run 'sif index update' first."</automated>
  </verify>
  <done>
  All five hints corrected to real commands (5 occurrences of the corrected update suggestion across the three files; the vsearch hint additionally names the real embed command). Live runs against a nonexistent SIF_DB_PATH print the corrected hints for status, search search, search vsearch, and bench. No src file contains the old nonexistent top-level command forms.
  </done>
</task>

<task type="auto">
  <name>Task 2: Fix docs/development.md examples and the two live skills' stale notes (DOC-04, DOC-02)</name>
  <files>docs/development.md, .claude/skills/sif-search/SKILL.md, .claude/skills/sif-get/SKILL.md</files>
  <action>docs/development.md has TWO blocks to fix:
  1. Debug-logging block (~lines 356-359, under a "via environment variable" lead-in): the invocation line using the bare top-level search form (the line directly after the export of SIF_LOG_LEVEL) becomes the BM25 group form with the query still quoted as `"query"`. Keep the export line unchanged.
  2. "Testing with Real Data" block (lines 436-446): replace the three stale command lines (a nonexistent collection-create taking a bare name, a nonexistent index-add taking name plus path, and a bare top-level search) so the block reads, in order: the existing SIF_DB_PATH export comment and export line unchanged; then a comment `# Add test data as a collection, then index and embed it`; then the collection command in README-canonical argument order — path positional first (`./test-data`), collection name via the required name option (`test`); then the index-group update command; then the index-group embed command; then the existing `# Run queries` comment; then the BM25 group form of the search command with `"test query"` quoted. All four commands are planner-proven real; do not invent flags.
  Skills (error-handling step 5 in each):
  3. .claude/skills/sif-search/SKILL.md:66 — the note about what to tell the user when stderr contains the no-index message names the nonexistent top-level update; change the inline-code command in that bullet to the index-group update command.
  4. .claude/skills/sif-get/SKILL.md:71 — same change for the no-index-exists bullet.
  Do NOT touch any other command in either skill (`sif -q search query`, `sif -q get get`, `sif -q get multi-get` forms are valid); do NOT touch ~/.claude/skills/docsift-* symlinks (they point into a different repo).
  </action>
  <verify>
    <automated>cd /Users/forrest/GitHub/SIF && ! grep -rn "sif update\|sif collection create\|sif index add\|sif search \"" docs/development.md .claude/skills/sif-search/SKILL.md .claude/skills/sif-get/SKILL.md && grep -c "sif index update" .claude/skills/sif-search/SKILL.md .claude/skills/sif-get/SKILL.md && env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/test_docs.py -q 2>&1 | tail -1 | grep -q "passed"</automated>
  </verify>
  <done>
  docs/development.md contains zero nonexistent command forms and its two fixed blocks use only planner-proven commands (collection add with path-positional + name-option, index update, index embed, BM25 group search). Both skills' error-handling notes name the real index-group update command. The Phase 06 docs validator suite still passes (development.md is not in its DOCS_FILES; the run guards against accidental damage to validated docs).
  </done>
</task>

<task type="auto">
  <name>Task 3: Repo-wide stale-command sweep, existence proofs, full quality suite</name>
  <files>src/sif/cli/main.py, src/sif/cli/commands/bench.py, src/sif/cli/commands/search.py, docs/development.md, .claude/skills/sif-search/SKILL.md, .claude/skills/sif-get/SKILL.md</files>
  <action>Verification-only unless the sweep finds genuinely stale remnants — then fix them under the same rules (only real commands from the verified surface; string-only edits).
  1. Sweep ALL user-facing surfaces for the four stale patterns (nonexistent top-level update; collection-create; index-add; bare quoted top-level search) plus bare top-level embed/query/vsearch forms: run one recursive grep over src/, docs/, .claude/skills/sif-get, .claude/skills/sif-search, README.md, CLAUDE.md. Expected: zero hits (planner's sweep already found and listed every hit, including the one beyond the audit at docs/development.md:358). Treat any surviving hit as a fix, not a waivable note.
  2. Existence proof: run `--help` for each distinct command named in the corrected text and cite the usage line in the summary: `python -m sif.cli.main index update --help`, `index embed --help`, `collection add --help`, `search search --help` (all under `env -u FORCE_COLOR NO_COLOR=1`). Each must exit 0 and print a Usage line.
  3. Full quality suite per CLAUDE.md: `ruff check src tests`; `ruff format --check src tests`; `env -u FORCE_COLOR NO_COLOR=1 python -m pytest`. Baseline is 675 passed / 0 failed (STATE.md, post 260914-vyr). If exactly the two known order-dependent caplog tests in tests/unit/embedding/test_openai_embedder.py fail, rerun that file in isolation to confirm they pass alone (pre-existing, WINDOWS.md #3/#4) and note it; anything else failing is a regression from this task's string edits and must be fixed before done.
  </action>
  <verify>
    <automated>cd /Users/forrest/GitHub/SIF && ! grep -rn "sif update\|sif collection create\|sif index add\|sif search \"\|sif embed \|sif query \|sif vsearch " src/ docs/ README.md CLAUDE.md .claude/skills/sif-get .claude/skills/sif-search && env -u FORCE_COLOR NO_COLOR=1 python -m sif.cli.main index update --help >/dev/null && env -u FORCE_COLOR NO_COLOR=1 python -m sif.cli.main index embed --help >/dev/null && env -u FORCE_COLOR NO_COLOR=1 python -m sif.cli.main collection add --help >/dev/null && env -u FORCE_COLOR NO_COLOR=1 python -m sif.cli.main search search --help >/dev/null && ruff check src tests && ruff format --check src tests && env -u FORCE_COLOR NO_COLOR=1 python -m pytest -q 2>&1 | tail -3</automated>
  </verify>
  <done>
  Zero stale-command references remain in src/, docs/, the two live skills, README.md, or CLAUDE.md. All four corrected commands proven via --help. ruff check and ruff format --check clean. Full pytest green at the 675 baseline (or the two documented pre-existing caplog tests confirmed order-dependent via isolated rerun). Summary cites the sweep grep output and the four usage lines.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

No new trust boundaries. This task edits user-facing hint strings and documentation only; no input parsing, no network, no auth, no dependency changes.

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-wxv-01 | Tampering | docs/development.md corrected block | low | accept | Replacement commands are planner-proven against the Click tree and re-proven via --help in Task 3; string-only edits cannot alter control flow. |
| T-wxv-02 | Information Disclosure | CLI hint strings | low | accept | Hints name only command names, no paths/secrets; correcting them strictly reduces misleading output. |
</threat_model>

<verification>
- Negative grep gates (Task 1-3 automated) return zero stale references across all user-facing surfaces, including the extra site at docs/development.md:358 found during planning beyond the audit list.
- Behavioral: live CLI runs against a nonexistent SIF_DB_PATH print the corrected hints (status / search search / search vsearch / bench).
- Existence: --help proofs for index update, index embed, collection add, search search, cited in the summary.
- Suite: ruff check + ruff format --check clean; full pytest at 675-passed baseline with the documented WINDOWS.md #3/#4 exception handling.
</verification>

<success_criteria>
- All 11 verified stale sites fixed (5 src hints, 2 skill notes, 4 docs lines across 2 blocks) and sweep confirms no others.
- Every command a user can be told to run actually exists.
- Suite green; no test edits required (none assert old hints — planning-verified).
</success_criteria>

<output>
Create `.planning/quick/260914-wxv-fix-stale-command-references-nonexistent/260914-wxv-SUMMARY.md` when done
</output>
