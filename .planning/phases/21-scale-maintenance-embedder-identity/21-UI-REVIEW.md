# Phase 21 — UI Review

**Audited:** 2026-11-18
**Baseline:** No UI-SPEC.md — abstract 6-pillar standards adapted to the Click/Rich terminal interface. No web frontend exists (no `.tsx`/`.jsx`/`.css`, no `components.json`). The audited surface is what this phase changed: `sif index vacuum` / `sif index backup` output and refusals, the `sif index embed` streaming/migrate/identity warnings, `sif status` vector-lag text, the `sif cleanup` reconcile line, and the embedder-identity mismatch/remedy messages on every host. `21-CONTEXT.md` D-01..D-20 and the plan acceptance criteria are the functional contract.
**Screenshots:** not captured — no web UI. Ports 3000/5173 were closed; port 8080 answered with an unrelated local service (as in the phase-19 audit), not a SIF surface. Real CLI renders were captured as text at 80/100/120 columns from the phase-21 completion tree (`a323a38`; the audited files have no diff from that tree to HEAD).
**Interaction captures:** off (`workflow.ui_interaction_capture` false). CLI interaction states were exercised manually: `index vacuum` (success, 80/120, missing index), `index backup` (default, `--output`, existing target, symlink target, missing index), `cleanup --yes`, `status` at 80/100/120, a synthetic pre-Phase-21 index opened twice (both migration warnings, then silence), and `index vacuum`/`backup`/`status`/`embed` help.

**Scope note:** Pillars that assume a rendered screen are adapted to their terminal equivalents: table/blocks hierarchy and width responsiveness, Rich style semantics, terminal typography (line length, wrapping, numeric formats), layout rhythm, and CLI state coverage.

**Registry audit:** skipped — no `components.json`.

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 3/4 | Identity/refusal/busy copy is specific and remedy-bearing, but the new shadow warning ships `for 1 documents`, the failure report hedges `document(s)`, and the only identity remedy (`--force`) is undocumented in help |
| 2. Visuals | 3/4 | Vacuum/backup/cleanup blocks are legible, but at 80 columns the backup path wraps into a three-line hanging value and the two migration warnings share identical weight |
| 3. Color | 3/4 | Semantic styles only and no color-only meaning, but the phase's primary safety signal — the identity-mismatch warning — bypasses Rich and is the only unstyled diagnostic |
| 4. Typography | 3/4 | Numeric formats are consistent, but both new warnings are single unbounded log lines (~160 and ~300 chars) that hard-wrap arbitrarily at the canonical 80 columns |
| 5. Spacing | 3/4 | Vacuum/backup/cleanup indentation and table padding are consistent; the two migration warnings and the status table run together with no separation |
| 6. Experience Design | 3/4 | State coverage is strong (refusals, busy, integrity, legacy migration), but a streaming embed has no progress feedback, vacuum silently reconciles the shadow, and backup success never confirms verification |

**Overall: 18/24**

No BLOCKER findings: every audited flow completes or fails with a specific, actionable message, and no defect removes data or blocks a task. All findings below are WARNING or minor.

---

## Top 3 Priority Fixes

1. **New count-bearing messages ship ungrammatical/hedged copy** — `Upgrading index: deriving the embedded-document shadow for 1 documents (one-time pass)` (captured live; `src/sif/database/schema.py:396-401`) and the failure summary `Embedding failed for 1 document(s)` / `... 1 collection(s)` (`src/sif/cli/commands/index.py:514-518`) read as machine output at the exact moment a user is being asked to trust a migration or a partial run. Use a plural helper (`1 document` / `N documents`) for both, and drop the `(s)` hedge in favor of the same helper. The pre-existing `N chunks embedded` line (`index.py:498`) has the same latent bug on a one-chunk document.
2. **Width discipline is missing for the new long diagnostics and backup path** — the identity-mismatch warning (~300 chars, `src/sif/embedding/identity.py:506-514`) and the legacy-assumption warning (~160 chars, `identity.py:421-426`) are emitted through a plain `logging.StreamHandler` (`src/sif/utils/logging.py:116-121`), so at 80 columns they hard-wrap at arbitrary character positions; `sif index backup` prints the resolved path unwrapped (`index.py:613-615`) and Rich breaks it after the label into a three-line hanging value (captured at 80). Route these through the Rich console with explicit wrapping (message first, then indented `stored:`/`current:`/`remedy:` lines), and print `Output:` with `soft_wrap=True`/`overflow="fold"`.
3. **Long-running and trust operations give no feedback** — `sif index embed` streams per document with no spinner or count (the loop at `src/sif/cli/commands/index.py:380-498` prints only `Already embedded` and the final total), even though `index update` already uses a Rich spinner; `vacuum_index` reconciles the shadow silently while `sif cleanup` prints its counts (`src/sif/cli/main.py:276-281`); and `Backup complete` never confirms the `PRAGMA integrity_check` the help promises (`index.py:571-577, 613-615`). Add a Progress task with document/vector counts, print the vacuum reconcile counts in the cleanup style, and print `integrity_check: ok` on backup success.

---

## Detailed Findings

### Pillar 1: Copywriting (3/4)

**WARNING — the one-time shadow warning is ungrammatical for a single document.** The format string is `"... for %d documents (one-time pass)"` with no singular branch (`src/sif/database/schema.py:396-401`). Live capture on a legacy index:
```
WARNING: Upgrading index: deriving the embedded-document shadow for 1 documents (one-time pass)
```
The count is correct and the once-only behavior is stated; only the inflection is wrong. This is the first line a user sees when a large index upgrades, so it carries disproportionate trust weight.

**WARNING — the new failure report hedges with `(s)`.** `Embedding failed for {len(failed_collections)} collection(s)` and `... {len(failed_documents)} document(s)` (`src/sif/cli/commands/index.py:514-518`). On a single-document failure the final ClickException reads `Embedding failed for 1 document(s)` — the summary of a partial run should be exact.

**WARNING — the only identity remedy is absent from help.** Every identity warning/error names `sif index embed --force` (`identity.py:421-426, 506-514`; `index.py:371-377`; `hybrid.py:34-37`), but `index embed --help` describes `-f, --force` only as `Force re-embed all documents` (`index.py:266-283`). The certification semantics (D-04) are documented in `docs/architecture.md:831-832` but not discoverable where the user is told to run the command. Add one sentence to the option help (e.g., "also certifies a legacy-assumed embedder identity when the run is complete and unfiltered").

**Minor — new maintenance help is one line and omits the enforced constraints.** `index vacuum --help` says `Reclaim unused space in the index database.` and `index backup --help` says `Create a verified backup copy of the index database.` with `--output` described only as `Destination file for the verified backup copy` (`index.py:527-530, 571-577`). The commands actually refuse below 2x free space, refuse existing/symlink/DB/sidecar targets, and verify with `integrity_check`; none of that is visible before running. A two-line notes block would prevent avoidable retries.

**Minor — backup reports the resolved path, not the requested one.** On macOS a `SIF_DB_PATH` under `/var/...` is reported as `/private/var/...` (`index.py:613-615`; live capture). The path works, but a user comparing it with their `--output` argument sees a different string. Label it `Resolved output:` or print the argument when supplied.

**Minor — `sha256:<16 hex>` is unexplained in the warning.** `assuming sha256:a8290b039dcd5cad (modelscope:Qwen/Qwen3-Embedding-0.6B)` names the identity but not what the token is. Prefixing `identity ` or `fingerprint ` costs two words and makes the display_fingerprint convention self-describing.

**Pass — errors and refusals are specific and remedy-bearing.** Live: `Refusing to back up to …: the target already exists. Choose a new path or remove the existing file.` and `... the target is a symlink.`; the low-disk error includes required and available bytes/MiB in the index directory (`maintenance.py:160-168`); busy errors say `Retry once active readers finish` / `Retry once the other index writer or reader has finished` (`maintenance.py:155-158, 188-191`); the dim mismatch names `database has FLOAT[n], but settings require FLOAT[m]` plus the restore/rebuild remedy (`identity.py:270-277`). No `Submit`/`OK`/`No data`/`went wrong` placeholders exist on this surface. `sif status` and both maintenance commands refuse a missing index with `Run 'sif index update' first` and do not create a file (verified).

### Pillar 2: Visuals (3/4)

**WARNING — the backup path value breaks the label/value layout at 80 columns.** Source: `console.print(f"  Output: {result.output}")` (`src/sif/cli/commands/index.py:614`) with no `soft_wrap`/`overflow`. Live 80-column capture:
```
Backup complete:
  Output:
/private/var/folders/.../backups/
sif-20261118T072449Z.db
  Size: 253952 bytes (0.24 MiB)
```
The continuation lines lose the two-space indent, so `Size:` appears to align with a different value than `Output:`. At 120 the same path fits on one line and the block reads cleanly.

**WARNING — serious and benign warnings have identical visual weight.** On a legacy index, the status render opens with two `WARNING:` lines of the same color and weight (`identity.py:421-426`, `schema.py:396-401`); the identity mismatch that requires action and the one-time shadow derivation that requires none are indistinguishable until the reader parses both sentences. A blank line and a short prefix (e.g., `Migration:`) would separate them.

**Minor — the embed run has no focal point while work is in progress.** The loop prints only dim `Already embedded` lines (`index.py:434`); there is no counter, spinner, or current-document line, so the terminal is static for the duration of the run. See Pillar 6.

**Pass — the new blocks otherwise read correctly.** `Vacuum complete:` / `Backup complete:` / `Cleanup complete:` are green titles followed by 2-space-indented values; the cleanup reconcile line joins the existing bullet list without breaking alignment; the status table keeps its title/header/padding and the new `Vector lag` row sits in the same visual rhythm; stale results carry a dim `(stale vectors)` annotation on the title (`src/sif/cli/commands/search.py:169-170, 446-447`) plus one yellow stderr hint (`search.py:313-327`), so marking is visible without a new column.

### Pillar 3: Color (3/4)

**WARNING — the primary safety diagnostic is the only unstyled message.** The identity-mismatch warning and the legacy-assumption warning are `logger.warning(...)` calls (`src/sif/embedding/identity.py:421-426, 506-514`) routed through a plain `logging.Formatter`/`StreamHandler` (`src/sif/utils/logging.py:116-121`) with no Rich markup. Every other new surface uses semantic Rich styling: success titles are `green` (`index.py:565, 613`), failures `red` (`index.py:501-505, 513`), the stale hint `yellow` (`search.py:325`), and stale annotations `dim` (`search.py:170`). The phase's most actionable message therefore has less visual emphasis than the remedy hint beside it — and no color at all even when the terminal supports it.

**Minor — no severity differentiation between mismatch and migration.** Both render as `WARNING:` with identical color and weight (see Pillar 2). Color is correctly not the only signal, but it is unused where severity differs.

**Pass — no hardcoded colors and no color-only meaning.** The audited surface uses Rich semantic names only (`green`, `red`, `yellow`, `dim`); no hex/rgb values. `NO_COLOR=1` renders every captured report fully readable (all captures above were made under `NO_COLOR=1`), warnings remain visible through their `WARNING:` prefix, and the stale/mismatch signals are text-backed.

### Pillar 4: Typography (3/4)

**WARNING — both new warnings are unbounded single lines.** The mismatch message (`identity.py:506-514`) interpolates two 16-hex fingerprints and two full `cache_model_id` strings; the legacy message (`identity.py:421-426`) interpolates a fingerprint and a model id. Live capture at `COLUMNS=100` produced lines longer than 100 characters because the logger does not consult the terminal width; at 80 they hard-wrap mid-token in the emulator. Nothing is lost, but the sentence that contains the remedy can split across three lines at arbitrary points. Structured multi-line output (`stored: …`, `current: …`, `remedy: …`) would be stable at every width.

**Minor — `(s)` and `%d documents` hedging** (cross-referenced under Pillar 1). The new copy does not maintain the singular/plural discipline of the surrounding CLI.

**Minor — the backup path is unbreakable and not foldable.** The same path that wraps at 80 (`index.py:614`) contains no spaces, so Rich can only wrap at slashes/characters; the result is a hanging line rather than a deliberate fold.

**Pass — numeric and identifier typography is consistent.** `_format_bytes` is used identically by vacuum and backup (`index.py:522-524`): `253952 bytes (0.24 MiB)`, integer bytes plus two-decimal MiB. Fingerprints are uniformly `sha256:<16 hex>` (`identity.py:162`); widths render as `FLOAT[n]`; status counts are plain integers; the cleanup/vacuum/backup blocks share the same two-space indent and decimal precision.

### Pillar 5: Spacing (3/4)

**WARNING — migration warnings and the status table have no separation.** The two `WARNING:` lines print immediately before the `Index Status` table with no blank line (`sif status` live capture), so on stderr-merged terminals the first table border visually attaches to the warnings. One blank line after the warning block (or a leading blank before the table) would create the missing section break.

**Minor — the wrapped backup value breaks the indent rhythm** (`index.py:613-615`): continuation lines start at column 0 while `Size:` starts at column 2 (see Pillar 2). Fixing the wrap restores the two-line label/value spacing.

**Minor — vacuum has no blank line between the title and its values.** `Vacuum complete:` is followed immediately by `  Before:`; this matches the compact style of `Backup complete:` and `Cleanup complete:`, so it is consistent, but the block is dense for a three-metric result. Optional.

**Pass — spacing values are consistent across the phase surface.** Rich default table padding is untouched; the cleanup reconcile line uses the same `  - ` bullet prefix and count format as the pre-existing cleanup lines (`src/sif/cli/main.py:276-281`); the status table gains a row without changing column widths; no arbitrary padding or ad-hoc blank-line counts were introduced.

### Pillar 6: Experience Design (3/4)

**WARNING — the streaming embed has no progress feedback.** The SCALE-03 rewrite streams per document and commits per document (`src/sif/cli/commands/index.py:380-498`); during that loop the only output is dim `Already embedded: <path>` for skipped documents and the final `Embedding complete: N chunks embedded`. On a personal KB large enough to motivate the phase, a user cannot distinguish a healthy long run from a hung model load. `Progress`/`SpinnerColumn`/`TextColumn` are already imported and used by `index update` (`index.py:14, 114-118`), so the machinery exists; add a task with `done/total documents` and current path.

**WARNING — `sif index vacuum` repairs the shadow silently.** `vacuum_index` calls `reconcile_embedded_documents` (per D-10) but the CLI prints only before/after/reclaimed (`src/sif/cli/commands/index.py:565-568`; helper at `src/sif/database/maintenance.py:126-172`). `sif cleanup --yes` prints `Reconciled embedded-document markers: 0 removed, 0 added` (`src/sif/cli/main.py:280-281`, live capture). A vacuum that silently changes derived state is inconsistent and gives the user no evidence the repair happened.

**WARNING — backup success does not confirm verification.** Help says `Create a verified backup copy` and `--output` says `Destination file for the verified backup copy` (`index.py:571-577`), and the implementation does require `PRAGMA integrity_check == [('ok',)]` (`maintenance.py:387-397`), but the success block prints only `Output` and `Size` (`index.py:613-615`). The user must trust the adjective instead of seeing the check. Print `Verified: integrity_check ok` (and optionally the `0600` mode) on success.

**Minor — a 0-byte vacuum result has no explanation.** `Reclaimed: 0 bytes (0.00 MiB)` (live capture) is accurate but ambiguous; a clause such as `(database already compact)` distinguishes "nothing to do" from "the command did nothing".

**Minor — `sif index embed` completion omits the document count.** `Embedding complete: N chunks embedded` (`index.py:498`) does not say how many documents were processed or skipped, which matters after the per-document streaming rewrite and the resumable skip path.

**Pass — the new interaction states are otherwise strong.** Missing indexes are refused before any file is created, with `Run 'sif index update' first` and exit 1 (verified for both vacuum and backup); existing and symlink targets are refused before a connection opens (verified, exit 1, path + reason); busy/locked and low-disk failures are retryable, non-zero, and traceback-free; the legacy index upgrades on the first open with exactly two one-time warnings and is silent on the second open (verified); the shadow migration is marker-gated and idempotent; `cleanup` keeps its confirmation (`--yes` bypasses it, `Aborted!` on decline); stdout stays clean for machine formats while identity/stale hints go to stderr; and a same-dimension mismatch warns once per process while every row is marked `(stale vectors)` in tables/CSV/Markdown/XML (`search.py:169-170, 313-327, 422-476`), with `sif index embed` failing before writing any vector (`index.py:361-377`).

---

## Minor Recommendations (not in top 3)

1. Pluralize `%d documents` in the shadow backfill warning and drop `(s)` from the failure report; add a one-chunk case to the completion line (`schema.py:398`, `index.py:498, 514-518`).
2. Add a `--force` certification sentence to `index embed --help` and the 2x-free-space / target-refusal / verification constraints to the vacuum and backup help (`index.py:266-283, 527-530, 571-577`).
3. Emit the identity-mismatch and legacy-assumption warnings as a short Rich block with `stored:`/`current:`/`remedy:` lines so they wrap deliberately at 80 (`identity.py:421-426, 506-514`).
4. Print `Output:` with `soft_wrap=True`/`overflow="fold"`, or print the requested path and label the resolved one separately (`index.py:614`).
5. Add one blank line between the migration-warning block and the status table.
6. Print the vacuum reconcile counts in the cleanup bullet style (`index.py:565-568`, `maintenance.py:126-172`).
7. Print `Verified: integrity_check ok` (and the `0600` mode) on backup success (`index.py:613-615`).
8. Add a Rich progress task with document/vector counts to the streaming embed loop (`index.py:380-498`).
9. Explain `sha256:<16 hex>` as the identity fingerprint in the warning text (`identity.py:421-426`).
10. Add `(database already compact)` for a zero-reclaim vacuum and the processed/skipped document counts to the embed completion line.
11. State that watcher embedding resumes on the next watch session after `Embedding disabled for this watch session` (`src/sif/indexing/watcher.py:300, 349`).

---

## Files Audited

- `src/sif/cli/commands/index.py` (phase-21 completion tree): `embed_cmd` streaming loop and failure report (`380-520`), `_format_bytes` (`522-524`), `index vacuum` (`527-568`), `index backup` (`571-615`), identity resolution/refusal (`222-239, 348-377`).
- `src/sif/database/maintenance.py`: `vacuum_index` (`126-192`), target refusals (`213-246`), `_verify_backup` (`251-262`), `backup_index` (`356-397`).
- `src/sif/database/schema.py`: shadow DDL/backfill and the one-time warning (`364-404`), `drop_all` ordering.
- `src/sif/embedding/identity.py`: `display_fingerprint` (`162`), shared dimension wording (`230-277`), `ensure_legacy_identity` warning (`406-427`), `warn_identity_mismatch_once` (`496-514`).
- `src/sif/search/hybrid.py`: `SEARCH_DIMENSION_REMEDY` / `search_dimension_error` (`32-52`), pipeline identity policy (`285-430`).
- `src/sif/cli/commands/search.py`: `_dimension_refusal` (`87-92`), stale annotation and hint (`169-170, 313-327, 422-476`), vsearch/query identity wiring (`827-872, 1148-1199`).
- `src/sif/cli/main.py`: `_vector_lag_text` (`147-171`), status row (`220-228`), cleanup confirmation and reconcile line (`236-281`).
- `src/sif/indexing/embed_writer.py`: validation error text (`48-123`).
- `src/sif/indexing/watcher.py`: identity adoption and disabled-session event (`236-300, 320-356`).
- `src/sif/utils/logging.py`: plain Formatter/StreamHandler (`116-121`).
- `docs/cli-reference.md` (generated `index vacuum` 460+, `index backup` 405+), `docs/configuration.md` (prompt settings 63-64), `docs/architecture.md` (identity/shadow/streaming/maintenance sections 642, 793, 821-866).
- `tests/unit/database/test_maintenance.py`, `tests/integration/test_maintenance.py`, `tests/unit/cli/test_index.py`, `tests/unit/cli/test_main.py`, `tests/unit/embedding/test_identity.py` (read for the behavioral contract; all states exercised through the CLI).
- Live text captures from the phase-21 completion tree (`a323a38`, no diff to HEAD for these files): `index vacuum`/`index backup`/`index embed`/`status` help at 80; `status` at 80/100/120 for empty and 2-document indexes; `index vacuum` at 80/120; `index backup` default at 120 and 80 (path wrap); `index backup --output` existing/symlink refusals at 80; `index vacuum`/`index backup` with no index; `cleanup --yes` reconcile output; a synthetic pre-Phase-21 index opened twice (identity-assumed + shadow-backfill warnings, then silence).
