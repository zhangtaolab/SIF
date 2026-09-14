---
phase: 260914-wxv-fix-stale-command-references-nonexistent
plan: 01
subsystem: cli
tags: [cli, click, docs, hints, doc-02, doc-04]

requires:
  - phase: 07-cli-claude-skill
    provides: the two live skills (.claude/skills/sif-search, sif-get) whose error-handling notes were corrected
provides:
  - Every user-facing "No index found" hint names only real, executable commands (sif index update / sif index embed)
  - docs/development.md Testing-with-Real-Data and debug blocks contain only executable commands
  - Both live skills' no-index error notes point at `sif index update`
affects: [v1.0 milestone close, docs audit, skills]

actuals:
  tokens: 214
  tasks: 3
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Hint strings name command-group-qualified forms (`sif index update`, never a bare top-level verb)"

key-files:
  created: []
  modified:
    - src/sif/cli/main.py
    - src/sif/cli/commands/bench.py
    - src/sif/cli/commands/search.py
    - docs/development.md
    - .claude/skills/sif-search/SKILL.md
    - .claude/skills/sif-get/SKILL.md

key-decisions:
  - "search.py vsearch hint uses multi-line implicit string concatenation to keep the corrected text under the 100-char ruff E501 limit while printing the exact planned message"
  - "Bare 'No index found.' messages (collection.py:137, main.py:145) left untouched per plan — they name no command and are not misleading"

requirements-completed: [DOC-02, DOC-04]

coverage:
  - id: D1
    description: "All five CLI 'No index found' hints (main.py status, bench.py, search.py search/vsearch/query) name real index-group commands; vsearch also names the real embed command"
    requirement: DOC-02
    verification:
      - kind: other
        ref: "negative grep src/ for 'sif update|sif embed ' -> zero hits; grep -c \"Run 'sif index update'\" across 3 files -> 5"
        status: pass
      - kind: e2e
        ref: "live runs vs nonexistent SIF_DB_PATH: status -> \"Run 'sif index update' to create one.\"; search search/query + bench -> \"Run 'sif index update' first.\"; search vsearch -> \"and 'sif index embed' first.\""
        status: pass
    human_judgment: false
  - id: D2
    description: "docs/development.md Testing-with-Real-Data and debug blocks use only real commands; both live skills' error notes name `sif index update`"
    requirement: DOC-04
    verification:
      - kind: other
        ref: "negative grep docs/development.md + both SKILL.md for 'sif update|sif collection create|sif index add|sif search \"' -> zero hits"
        status: pass
      - kind: unit
        ref: "tests/test_docs.py -q -> 12 passed (validator suite unharmed; development.md not in DOCS_FILES)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Repo-wide sweep: zero stale command references remain across src/, docs/, README.md, CLAUDE.md, and the two live skills; every corrected command proven via --help"
    requirement: DOC-02
    verification:
      - kind: other
        ref: "grep -rn 'sif update|sif collection create|sif index add|sif search \"|sif embed |sif query |sif vsearch ' src/ docs/ README.md CLAUDE.md .claude/skills/{sif-get,sif-search} -> exit 1 (zero hits)"
        status: pass
      - kind: other
        ref: "--help existence proofs, all exit 0: 'Usage: python -m sif.cli.main index update [OPTIONS]'; 'index embed [OPTIONS]'; 'collection add [OPTIONS] PATH'; 'search search [OPTIONS] QUERY'"
        status: pass
      - kind: unit
        ref: "ruff check src tests -> All checks passed; ruff format --check -> 132 files already formatted; env -u FORCE_COLOR NO_COLOR=1 python -m pytest -q -> 675 passed in 14.90s (baseline matched)"
        status: pass
    human_judgment: false

duration: 6min
completed: 2026-09-14
status: complete
plan_head_before: d509290
---

# Quick Task 260914-wxv: Stale Command References to Nonexistent Commands Summary

**Corrected 11 user-facing stale command references (5 CLI hints, 4 docs lines across 2 blocks, 2 skill notes) so every suggested command actually exists; suite green at the 675 baseline.**

## Performance

- **Duration:** ~6 min (15:51:02Z - 15:56:19Z)
- **Tasks:** 3/3
- **Files modified:** 6
- **Commits:** 2 task commits (verification-only Task 3 required no additional commit — sweep found zero remnants)

## Accomplishments

- All five CLI "No index found" hints now name the real index-group commands: `sif index update` (main.py status, bench.py, search.py search/query) and `sif index update` + `sif index embed` (search.py vsearch, which previously misnamed both commands)
- docs/development.md "Testing with Real Data" block now uses the README-canonical forms: `sif collection add ./test-data --name test`, `sif index update`, `sif index embed`, `sif search search "test query"`; the debug block uses `sif search search "query"`
- Both live skills' error-handling notes (sif-search SKILL.md:66, sif-get SKILL.md:71) tell users to run `sif index update`
- Repo-wide sweep confirms zero stale forms remain; all four corrected commands proven live via `--help`

## Task Commits

1. **Task 1: Correct the five CLI hint strings in src/** - `3d79659` (fix)
2. **Task 2: Fix docs/development.md examples and the two live skills' stale notes** - `484b82c` (fix)
3. **Task 3: Repo-wide sweep, existence proofs, full quality suite** - verification only, no commit (sweep clean; nothing to fix)

## Files Created/Modified

- `src/sif/cli/main.py` - status hint: `sif update` -> `sif index update` to create one
- `src/sif/cli/commands/bench.py` - bench hint: `sif update` -> `sif index update`
- `src/sif/cli/commands/search.py` - search/query hints -> `sif index update`; vsearch hint -> `sif index update` and `sif index embed`
- `docs/development.md` - debug block + Testing-with-Real-Data block rewritten to real commands
- `.claude/skills/sif-search/SKILL.md` - error-handling note -> `sif index update`
- `.claude/skills/sif-get/SKILL.md` - error-handling note -> `sif index update`

## Decisions Made

- vsearch hint reflowed as multi-line implicit string concatenation: the corrected single-line string would be ~104 chars, over the enforced ruff E501 limit of 100; the printed text is byte-identical to the plan's specified message
- Bare "No index found." messages (collection.py:137, main.py:145) left untouched per plan — they suggest no command and cannot dead-end a user

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - verify-command typo] Task 1 verify invoked bench with a nonexistent option**
- **Found during:** Task 1 (behavioral verify)
- **Issue:** Plan's verify ran `bench --fixture /dev/null`, but bench's CLI takes FIXTURE as a positional argument (`Usage: bench [OPTIONS] FIXTURE`); Click rejected `--fixture` with exit 2
- **Fix:** Corrected the invocation to `bench /dev/null`; no source change was needed — the hint itself was already correct
- **Files modified:** none (verify-command correction only)
- **Verification:** `python -m sif.cli.main bench /dev/null` against a nonexistent SIF_DB_PATH prints `No index found. Run 'sif index update' first.`
- **Committed in:** n/a (no code change)

---

**Total deviations:** 1 auto-fixed (verify-command typo; zero code impact)
**Impact on plan:** None — all planned edits landed exactly as specified.

## Issues Encountered

- A batched `--help` loop failed under zsh because unquoted `$cmd` does not word-split (each command was passed as one argument containing a space); rerunning the four invocations explicitly produced exit 0 and the expected usage lines for all four commands
- `git add` printed ignored-path advice for `.claude/` (the directory is in .gitignore), but both SKILL.md files are git-tracked since Phase 07 and staged normally; the Task 2 commit includes them

## Verification Evidence

Sweep (zero hits, exit 1):

```
grep -rn "sif update\|sif collection create\|sif index add\|sif search \"\|sif embed \|sif query \|sif vsearch " \
  src/ docs/ README.md CLAUDE.md .claude/skills/sif-get .claude/skills/sif-search
# (no output — zero stale references)
```

Existence proofs (all exit 0):

```
Usage: python -m sif.cli.main index update [OPTIONS]
Usage: python -m sif.cli.main index embed [OPTIONS]
Usage: python -m sif.cli.main collection add [OPTIONS] PATH
Usage: python -m sif.cli.main search search [OPTIONS] QUERY
```

`collection add --help` additionally shows `-n, --name TEXT  Collection name  [required]`, confirming the README-canonical `sif collection add PATH --name NAME` form used in the rewritten docs block.

Quality suite: `ruff check src tests` -> All checks passed; `ruff format --check src tests` -> 132 files already formatted; `env -u FORCE_COLOR NO_COLOR=1 python -m pytest -q` -> **675 passed** in 14.90s (exact baseline; the two known order-dependent caplog tests in tests/unit/embedding/test_openai_embedder.py did not surface this run, so no isolated rerun was needed).

## User Setup Required

None.

## Next Phase Readiness

- v1.0 audit DOC-02/DOC-04 (integration Finding 7) closed: no user-facing surface directs users at a nonexistent command
- Remaining pre-close items per STATE.md: phases 06/07 verification and typing debt (139 mypy errors), then /gsd-complete-milestone

## Known Stubs

None — string-only edits; no stubs introduced.

## Self-Check: PASSED

All 7 files verified present on disk; both task commits (3d79659, 484b82c) verified in git history.

*Completed: 2026-09-14*
