# Phase 22 — UI Review

**Audited:** 2026-11-18
**Baseline:** No UI-SPEC.md — abstract 6-pillar standards adapted to a Python CLI/MCP project. No web frontend exists (no `.tsx`/`.jsx`/`.css`/`.scss` in `src/`, no `components.json`). The audited surface is the agent-facing surface this phase shipped: the seven MCP tool descriptions/annotations and the `structuredContent`/text envelope, `sif mcp` help and daemon output, `/health` and `/mcp` transport-security responses, the Claude Code plugin/skill text (`sif-search`, `sif-get`, `sif-cite`), and citation/`get` output.
**Screenshots:** not captured — no web UI exists. Ports 3000 and 5173 were closed; port 8080 answered but serves an unrelated SearXNG instance (verified: SearXNG title, `/health` 404), not a SIF surface. Real CLI/protocol renders were captured as text at 80/100/120 columns, plus a live `sif mcp stdio` JSON-RPC session and a live `sif mcp http` security matrix.
**Interaction captures:** off (`workflow.ui_interaction_capture` false). Interaction was exercised directly instead: `tools/list`, `status`, `lex_search`, a `lex:`-prefixed `query`, full/ranged/path `get`, `metadata`, invalid-filter and missing-document errors over the real stdio server; `/health` with an allowed and a spoofed Host; `/mcp` with a spoofed and an allowed Origin; `mcp daemon --stop`; and `sif mcp {,http,daemon,stdio} --help` at 80/100/120 columns.

**Tree anchor:** source, plugin, and skill files are unchanged since the phase-22 completion tree (`10e2f6d5`); only `README.md` and `docs/mcp-server.md` changed later, and the findings below were re-verified at HEAD (`24c3828`). Line references are to HEAD for source/skills and to HEAD for the docs claim (which persists).

**Scope note:** Pillars that assume a rendered screen are adapted to terminal/agent equivalents: structured-output hierarchy in place of layout, annotation/state semantics in place of color, naming/casing consistency in place of type scale, CLI help wrapping and payload density in place of spacing, and tool-state coverage in place of interaction states. D-05..D-17 and the plan acceptance criteria are the functional contract for copy and transparency findings.

**Registry audit:** skipped — no `components.json` (not a shadcn/frontend project).

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 2/4 | README/docs assert the Registry listing that 22-07 recorded as blocked/not listed; the `docsif[mcp]` remedy is stale after `mcp` became core; skills/docs promise snippet/line-range fields that `lex_search`/`vec_search` never return |
| 2. Visuals | 3/4 | Output schemas are complete and consistent, but lex/vec result rows are dominated by four null citation fields and citation-relevant identity is split between the row and `metadata` |
| 3. Color | 4/4 | Honest read-only annotations, consistent `isError`/HTTP-status semantics, no color-only meaning, `NO_COLOR` clean |
| 4. Typography | 3/4 | `docid` vs `doc_id` drift in descriptions/docs/skills, and snake_case result fields beside the frozen camelCase metadata envelope |
| 5. Spacing | 4/4 | All four `sif mcp` help pages fit and wrap cleanly at 80 columns and are stable at 100/120; no truncation or arbitrary padding |
| 6. Experience Design | 2/4 | BLOCKER: `min_score` on the new MCP search tools drops the best-ranked matches first; `query` also degrades to BM25 with no in-band signal |

**Overall: 18/24**

---

## Top 3 Priority Fixes

1. **BLOCKER — `min_score` on `lex_search`/`vec_search` (and `query`) removes the strongest matches first** — every agent that sets a "minimum score" loses its best evidence and keeps the weakest. Live proof on a 40-document corpus: rank 1 `d0` displays `0.2000`, rank 2 `d1` `0.2233`, rank 3 `d2` `0.3043`; `min_score=0.21` drops rank 1, and `min_score=0.25` leaves only the weakest match. The MCP docs call it "Minimum score threshold" (`docs/mcp-server.md:134`) and phase 22 newly exposes it on two tools (`src/sif/mcp/tools.py:316-319, 357-359`). Carried from Phase 19, but newly shipped on `lex_search`/`vec_search`. Fix the score map to increase with relevance (for example `1 - 1/(1+|rank|)`), derive the pre-pagination SQL threshold from the same expression (`rank <= -m/(1-m)` for that map), keep ordering and global ranks unchanged, and add a regression asserting `min_score` never removes rank 1 before a weaker rank survives (`src/sif/search/bm25.py:77-97, 170-171, 231-232`).
2. **Citation fields are promised but null on two of the three search tools** — `sif-search` says results carry `snippet`, line range, and content hash, and the docs' citation workflow applies that to `query`, `lex_search`, and `vec_search`; live captures show `lex_search` and `vec_search` always return `snippet: null`, `line_start: null`, `line_end: null` (and so does a `lex:`-prefixed or degraded `query`). An agent following the skill has no usable line window on those routes and may cite a null range. Either attach the snippet window on the direct routes (one content fetch, as the CLI does) or make the contract explicit in the tool descriptions, `skills/sif-search/SKILL.md:17-18`, and `docs/mcp-server.md:140-141, 203-221`, and pin that copy with a test (`src/sif/mcp/backend.py:440-442, 606-620, 670-700`).
3. **The shipped copy claims a Registry listing that does not exist** — `README.md:333` says "SIF is listed in the official MCP Registry" and `docs/mcp-server.md:334` says "The public listing is `io.github.zhangtaolab/sif`", while `22-07-SUMMARY.md` records the publish as **blocked** (`blocked no-github-login`) with the registry state `not listed (reachable)`. A user or Registry-aware host that follows the claim finds nothing. Reword to "Registry manifest checked in; listing pending maintainer authentication" until the publish checkpoint is actually completed, and keep the existing preflight/publish instructions.

---

## Detailed Findings

### Pillar 1: Copywriting (2/4)

**WARNING — the Registry claim is factually false in the shipped docs.** `README.md:333` — "SIF is listed in the official MCP Registry as `io.github.zhangtaolab/sif`." `docs/mcp-server.md:334` — "The public listing is `io.github.zhangtaolab/sif` in the official MCP Registry." The phase's own evidence says otherwise: `22-07-SUMMARY.md` §"Registry Publish Outcome — BLOCKED" records `blocked no-github-login`, no publish attempt, and `--check` reporting `not listed (reachable)`. This is the most damaging copy defect on the phase surface because it is a distribution promise, not just wording. The rest of the Registry section (preflight semantics, duplicate handling, re-run rule) is accurate and well written.

**WARNING — the stdio dependency remedy is stale after D-03.** `src/sif/cli/commands/mcp.py:105` still says `Install with: pip install docsif[mcp]`. Phase 22 made `mcp` a core dependency and reduced the `mcp` extra to a uvicorn-only compatibility alias (`pyproject.toml:63-69`); installing `docsif[mcp]` therefore no longer installs the module the error is about. Use `pip install docsif` (or `pip install --force-reinstall docsif`) for a missing `mcp`, and keep `docsif[http]` for the uvicorn-only HTTP path.

**WARNING — the agent skills and docs overpromise search-result fields.** `skills/sif-search/SKILL.md:17-18` says "Results carry docid, path, score, snippet, line range, content hash, and metadata" for all three strategies. Live stdio capture of `lex_search` and a `lex:`-prefixed `query` returns `"snippet": null, "line_start": null, "line_end": null` (content hash is present). The direct `lex`/`vec` backend paths deliberately bypass `_apply_snippets` (`src/sif/mcp/backend.py:440-442, 606-620, 670-700`), the `protocol.py` docstring admits the fields stay `None` there. `docs/mcp-server.md:140-141` makes the same blanket claim for `query`, and the citation workflow at `docs/mcp-server.md:207-209` tells the reader to use the search-time window for `lex_search`/`vec_search` too. `sif-cite` saves the citation flow by requiring `get`, but the discovery copy is wrong. The `lex_search`/`vec_search` tool descriptions (`src/sif/mcp/tools.py:79-87`) also omit the caveat.

**Minor — `docid` vs `doc_id`.** The `get` and `multi_get` descriptions say "Returns docid" (`src/sif/mcp/tools.py:64-72`), `docs/mcp-server.md:147` says "by path or docid", and the skills use "docid" in prose, while the actual wire field is `doc_id`. Use `doc_id` in field-level copy (keep "document ID" as the concept) so agents do not look for a `docid` key.

**Minor — `sif mcp` with no subcommand is undocumented.** `src/sif/cli/commands/mcp.py:72-86` starts the stdio server when no subcommand is given, but `sif mcp --help` only lists the three commands and says "MCP server commands." There is no "starting stdio" line, so a user running `sif mcp` sees a silent process. Either require a subcommand or state the default in the group help and print a one-line stderr notice (stdout must stay protocol-clean).

**Minor — `--reload` is a documented no-op.** `src/sif/cli/commands/mcp.py:115` says "Accepted for compatibility; currently has no effect." Honest, but a live CLI option that does nothing is a copy/UX smell; remove it or implement it.

**Minor — the missing-index warning is generic.** `src/sif/cli/commands/mcp.py:94-97` prints "No index found. Some features may not work." For an agent-first surface, name the remedy (`run `sif index update``) and say that search/status will be empty until then.

**Pass — no generic labels or empty-state placeholders.** No `Submit`/`OK`/`Click Here` patterns. Error copy is remedy-bearing: invalid filters return `filter.gt: "gt" requires a numeric value; field 'tags' got str`, a missing document returns `Document not found`, `vec_search` names the `docsif[embed]` remedy, and the daemon/stop/Registry-script outputs name the exact outcome (`MCP daemon stopped (PID N)`, `MCP daemon is not running.`, `OK registry: not listed (reachable) ...`).

### Pillar 2: Visuals (3/4)

**Minor — lex/vec result rows are null-heavy.** A live `lex_search` row renders as `doc_id, path, title, content: null, snippet: null, content_hash, line_start: null, line_end: null, score, highlights, metadata`. Four of the twelve fields carry no signal on the two new tools. This is the visual consequence of the documented no-snippet route: the row's most valuable citation fields are absent exactly where the skill says they exist. Either populate them or make the shape honest (see Pillar 1/6).

**Minor — citation identity is split across two levels.** `doc_id`, `path`, `score`, `snippet`, `line_start/end`, and `content_hash` are top-level, while `rank`, `collection_name`, `vectors_stale`, `chunk_id`, `sequence`, and `chunk_matches` sit inside `metadata` (`src/sif/mcp/backend.py:173-190`; live capture). An agent scanning for citation evidence must look in two places, and the staleness flag that limits confidence is the least prominent field. Group citation fields together and/or lift `vectors_stale` to the top level in a future additive revision.

**Minor — `status.size_bytes` is always null.** `CollectionInfo.size_bytes` is declared (`src/sif/mcp/protocol.py:66-73`) but `SearchBackend.get_status` never sets it (`src/sif/mcp/backend.py:851-871`), so every live status response carries `"size_bytes": null`. Populate it or drop it from the output schema; an always-null field trains agents to ignore the field.

**Pass — the structured surface is otherwise sound.** All seven tools publish a non-empty `outputSchema`; every tool returns both compact JSON text and `structuredContent` from the same model (verified on the wire); `metadata` keeps the frozen Phase 20 envelope with no wrapper key and no `filteredDocuments` without a filter; `get`/`multi_get` return `document`/`documents`+`errors` with clear hierarchy; resource errors and tool errors are distinct.

### Pillar 3: Color (4/4)

**Pass — annotation semantics are honest and consistent.** All seven tools carry `readOnlyHint: true` and `openWorldHint: false` (live `tools/list`), with no misleading idempotent/destructive hints; the descriptions contain no auto-approval or prompt-free claim. Errors are signalled through `isError: true` (verified for invalid filter and missing document) and HTTP semantic statuses (bad Host 421, bad Origin 403, allowed 200, non-JSON 400).

**Pass — no color-only meaning and no hardcoded styling.** The MCP surface is plain JSON with no ANSI. The CLI uses semantic Rich styles only (green start/stopped, yellow warnings/not-running, red failure), and all captures were made under `NO_COLOR=1` and remained complete and readable. `/health` returns `{"status":"ok"}` with 200/421 as documented.

### Pillar 4: Typography (3/4)

**Minor — `docid` vs `doc_id` casing.** See Pillar 1; the same drift appears in `src/sif/mcp/tools.py:66,70`, `docs/mcp-server.md:147`, and the skill frontmatter. The wire field is `doc_id`; the prose should match.

**Minor — snake_case results beside a camelCase envelope.** Search results, `get`, and `status` use `doc_id`, `line_start`, `content_hash`, `document_count`, while `metadata` uses `totalKeys`, `remainingKeys`, `builtIns`, `filteredDocuments` (`src/sif/mcp/protocol.py:265-282`). The camelCase envelope is frozen by Phase 20 and documented, so this is a naming-consistency note, not a contract change; call it out in the docs as deliberate so agents do not infer a convention error.

**Minor — stale internal docstrings in the preserved models.** `src/sif/mcp/protocol.py:117-123, 144-150` still says `lex_search`/`vec_search` "stays unregistered in Phase 19"/"Registration stays Phase 22", although both are registered. Maintainer-facing only, but it contradicts the shipped state.

**Pass — numeric and structural naming is otherwise consistent.** Tool names are snake_case, `MCP`, `HTTP`, and `stdio` are capitalized/spelled consistently, option names match the schemas, and the help text's Title Case is stable across the four commands.

### Pillar 5: Spacing (4/4)

**Pass — help layout is width-safe.** `sif mcp`, `sif mcp http`, `sif mcp daemon`, and `sif mcp stdio` help pages were captured at 80/100/120 columns. Every option and description fits at 80 (longest line 79 columns), `http`/`daemon` output is byte-identical at 100 and 120, and there is no truncation, ellipsis, or mid-word wrap. The daemon help's long prose block wraps cleanly and the option column stays aligned.

**Pass — payloads use deliberate density.** The legacy text channel is compact JSON by contract (D-05), while `structuredContent` is structured for clients; tool descriptions are single focused paragraphs with no arbitrary blank lines. `tools/list` is large because every output schema is inline, but it is generated protocol data, not a rendered layout.

### Pillar 6: Experience Design (2/4)

**BLOCKER — `min_score` drops the best-ranked matches first (carried from Phase 19; newly exposed on `lex_search`/`vec_search`).** The displayed score is `1/(1+|bm25 rank|)` (`src/sif/search/bm25.py:170-171, 231-232`), so the best match has the *lowest* score, while the threshold keeps scores at or above the value (`src/sif/search/bm25.py:77-97`). Live proof on a 40-document corpus: rank 1 `d0` = `0.2000`, rank 2 `d1` = `0.2233`, rank 3 `d2` = `0.3043`; `min_score=0.21` drops rank 1 and keeps ranks 2-3, `min_score=0.25` keeps only the weakest rank 3, and `min_score=0.305` returns `[]`. Phase 22 added the parameter to `LexSearchInput`/`VecSearchInput` and to the `lex_search`/`vec_search` schemas (`src/sif/mcp/protocol.py:129-131, 156-159`; `src/sif/mcp/tools.py:316-319, 357-359`), so the two brand-new tools ship a filter that removes the best evidence first. The docs call it "Minimum score threshold" (`docs/mcp-server.md:134`), which is the opposite of what it does at the top of the ranking. This must not ship on the agent surface without the display/filter fix.

**WARNING — `query` can degrade to BM25 with no in-band signal.** On a base (BM25-only) or `uvx` install, or after a failed embedder load, `hybrid_search` logs one warning to stderr and returns BM25 rows (`src/sif/mcp/backend.py:339-342, 443-453, 498-500`) with no `search_mode`/`degraded` field in the result. The `sif-search` skill says the default is hybrid and the docs' tool section says "Hybrid search" (`skills/sif-search/SKILL.md:15-16`; `docs/mcp-server.md:121-126`), so an agent can present keyword-only results as semantic/hybrid results without knowing. Add an additive mode/degraded marker to `QueryOutput` (or at least to the result metadata) and mention the behavior in the tool description and skill; the one-time warning is honest in logs but invisible to the model.

**WARNING — the citation workflow breaks on two of the three advertised search strategies.** Same evidence as Pillar 1: `sif-cite` step 2 says to record each candidate's snippet and line window for `query`, `lex_search`, or `vec_search`, but the latter two (and a prefixed/degraded `query`) always return nulls. The workflow still works because step 3 retrieves with `get`; the failure mode is an agent attempting to quote a null/empty snippet or to cite a line range it never received. Make the skill's step 2 strategy-aware or populate the fields.

**Minor — `sif mcp` with no subcommand silently becomes a stdio server.** `src/sif/cli/commands/mcp.py:72-86` dispatches to `mcp_stdio_cmd` with no banner and no hint. A terminal user gets a process that appears to hang; an agent gets a server with no indication of the transport. Require a subcommand or print a one-line stderr notice.

**Minor — `--reload` is accepted and ignored.** `src/sif/cli/commands/mcp.py:115`. A user passing it sees no reload; honest help text is not a substitute for the behavior.

**Pass — the new interaction states are otherwise strong.** The embedder is lazy and loaded once under a lock; `status`/`get`/`metadata`/`lex_search` never load a model; `lex:`/`vec:` prefixes are stripped before routing and a BM25 route never touches the loader; expected failures are `ToolError`s with remedy text and `isError=true` at the wire; `/health` returns 421 for a spoofed Host and 200 for loopback; `/mcp` returns 421/403/400 per the security contract; `mcp daemon --stop` reports the four outcomes and only targets the MCP PID; a cold stdio first query is protocol-clean; and every tool is dual-channel and read-only.

---

## Minor Recommendations (not in top 3)

1. Fix the `docsif[mcp]` remedy to `pip install docsif` and keep `docsif[http]` for uvicorn (`src/sif/cli/commands/mcp.py:105, 158`; `pyproject.toml:63-69`).
2. Document the `lex:`/`vec:`/`hyde:`/`expand:` prefixes in the `query` description and `sif-search` skill, including that prefixed routes do not populate snippet/line fields (`src/sif/mcp/backend.py:425-453`).
3. Make `sif mcp` no-subcommand behavior explicit (help + stderr notice, or require a subcommand) (`src/sif/cli/commands/mcp.py:72-86`).
4. Remove `--reload` or implement it (`src/sif/cli/commands/mcp.py:115`).
5. Name `sif index update` in the missing-index warning (`src/sif/cli/commands/mcp.py:94-97`).
6. Standardize on `doc_id` in field-level prose (`src/sif/mcp/tools.py:64-72`; `docs/mcp-server.md:147`; skill frontmatter).
7. Populate or drop `status.size_bytes` (`src/sif/mcp/protocol.py:72`; `src/sif/mcp/backend.py:851-871`).
8. Add an additive `search_mode`/`degraded` marker for BM25 fallback (or at minimum a metadata note) so agents can tell hybrid from keyword-only results (`src/sif/mcp/backend.py:339-342`).
9. Reword the Registry headline to "manifest checked in; listing pending maintainer authentication" until the publish checkpoint resolves (`README.md:333`; `docs/mcp-server.md:334`).
10. Update the stale "unregistered"/"stays Phase 22" docstrings in the preserved models (`src/sif/mcp/protocol.py:117-123, 144-150`).
11. Consider lifting `vectors_stale` out of `metadata` in a future additive revision; it is the confidence caveat an agent must surface.

---

## Files Audited

- `src/sif/mcp/tools.py` (442 lines): reviewed descriptions, `TOOL_ANNOTATIONS`, `_result` dual-channel builder, seven registrations, `ToolError` boundaries, `docs://` resource.
- `src/sif/mcp/app.py` (309 lines): composition root, transport-security allowlists and `/health` guard, stdio/HTTP runners, quiet ordering.
- `src/sif/mcp/protocol.py` (282 lines): result/document citation fields, query/lex/vec inputs with `min_score`, frozen `MetadataOutput`.
- `src/sif/mcp/backend.py` (875 lines): citation boundary map, `get_document`/`get_documents_by_pattern` ranges, lex/vec direct paths, lazy embedder, prefix-first routing, rerank soft-degrade.
- `src/sif/cli/commands/mcp.py` (268 lines): group default dispatch, stdio/http/daemon commands, options and help, daemon stop messaging, install remedies.
- `src/sif/search/bm25.py`: score map, pre-pagination `min_score` predicate, chunk-path threshold (for the blocker).
- `skills/sif-search/SKILL.md`, `skills/sif-get/SKILL.md`, `skills/sif-cite/SKILL.md`: frontmatter, MCP tool grants, untrusted-content warnings, citation discipline.
- `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.mcp.json`, `server.json`: names, versions, source, transport, no credentials/paths.
- `scripts/publish_registry.py`: preflight/publish output copy and idempotency.
- `docs/mcp-server.md` (HEAD, plus the phase-22 tree copy): tool sections, citation workflow, transport security, plugin install, Registry section.
- `README.md` (HEAD, plus the phase-22 tree copy): install paths, plugin section, Registry section, marker.
- `pyproject.toml`: core dependency and deprecated extras aliases.
- `tests/unit/mcp/` fixtures (read for intent): `test_tools.py`, `test_citations.py`, `test_plugin.py` seeding/contract patterns.
- Live captures (HEAD): `sif mcp|http|daemon|stdio --help` at 80/100/120; `mcp daemon --stop`; real `sif mcp stdio` JSON-RPC for `tools/list`, `status`, `lex_search`, `lex: query`, full/ranged/path `get`, `metadata`, invalid filter, missing document; `sif mcp http` with `/health` allowed/spoofed Host and `/mcp` spoofed/allowed Origin; a 40-document BM25 corpus probe for score/min-score direction; `get` past-end and `multi_get` no-match probes.
