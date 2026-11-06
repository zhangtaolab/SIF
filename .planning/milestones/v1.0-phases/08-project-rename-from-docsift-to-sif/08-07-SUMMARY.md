---
phase: 08-project-rename-from-docsift-to-sif
plan: 07
subsystem: claude-skills
key-files:
  created: []
  modified:
    - .claude/skills/sif-search/SKILL.md
    - .claude/skills/sif-get/SKILL.md
decisions: []
tags: [rename, branding, claude-skills, cli]
tech-stack:
  patterns: []
---

# Phase 08 Plan 07: Rename Claude Skill Directories and Update Command References

**One-liner:** Renamed Claude Skill directories from docsift-search/docsift-get to sif-search/sif-get and updated all CLI command references, descriptions, and error messages to use "sif" and "SIF" branding.

## What Was Done

Renamed the two Claude Skill directories and updated their SKILL.md contents to reflect the project rename from DocSift to SIF.

### Changes

| File | Change |
|------|--------|
| `.claude/skills/docsift-search/SKILL.md` → `.claude/skills/sif-search/SKILL.md` | Renamed directory; updated name, description, objective, all CLI examples, error messages |
| `.claude/skills/docsift-get/SKILL.md` → `.claude/skills/sif-get/SKILL.md` | Renamed directory; updated name, description, objective, all CLI examples, error messages |

### Specific Updates in Both SKILL.md Files

- **Frontmatter `name`**: `docsift-search` → `sif-search`, `docsift-get` → `sif-get`
- **Description**: "DocSift index" → "SIF index"
- **Objective**: "DocSift document index" → "SIF document index", "Requires docsift CLI" → "Requires sif CLI"
- **CLI command examples**: All `docsift -q ...` → `sif -q ...`
- **Error handling**: `docsift update` → `sif update`

## Verification

- `test -d .claude/skills/sif-search` — PASS
- `test -d .claude/skills/sif-get` — PASS
- `test ! -d .claude/skills/docsift-search` — PASS
- `test ! -d .claude/skills/docsift-get` — PASS
- `grep -q "name: sif-search" .claude/skills/sif-search/SKILL.md` — PASS
- `grep -q "name: sif-get" .claude/skills/sif-get/SKILL.md` — PASS
- `grep -q "sif -q search query" .claude/skills/sif-search/SKILL.md` — PASS
- `grep -q "sif -q get get" .claude/skills/sif-get/SKILL.md` — PASS
- `! grep -q "docsift" .claude/skills/sif-search/SKILL.md` — PASS (0 matches)
- `! grep -q "docsift" .claude/skills/sif-get/SKILL.md` — PASS (0 matches)
- `! grep -q "DocSift" .claude/skills/sif-search/SKILL.md` — PASS (0 matches)
- `! grep -q "DocSift" .claude/skills/sif-get/SKILL.md` — PASS (0 matches)

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- [x] `.claude/skills/sif-search/SKILL.md` exists and is correct
- [x] `.claude/skills/sif-get/SKILL.md` exists and is correct
- [x] Commit `d0e16ac` verified in git log
- [x] No unexpected file deletions
- [x] No untracked files left behind
