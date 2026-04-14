# Feature Landscape

**Domain:** Local markdown document search engine (qmd/docsift)
**Researched:** 2026-04-14
**Confidence:** MEDIUM

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| BM25 full-text search | Fast keyword search is the baseline for any document search tool | LOW | Already implemented via SQLite FTS5 |
| Collection management (add/list/remove/rename/show) | Users organize notes into multiple directories/vaults | LOW | Partially implemented; missing `update-cmd`, `include`/`exclude` |
| Document indexing with checksum dedup | Re-indexing must be incremental, not destructive | LOW | Already implemented |
| File retrieval (`get`, `multi-get`, `ls`) | Users need to read the actual documents after finding them | LOW | `get` exists; `multi-get` and `ls` are missing |
| Vector semantic search | Table stakes for modern local search; users expect "meaning" matching | MEDIUM | Partially implemented; stubbed embedder fallback exists |
| Hybrid search (BM25 + vector fusion) | Neither keyword nor vector alone is sufficient for quality | MEDIUM | Already implemented with RRF (k=60) |
| Multiple output formats (JSON, CSV, Markdown, XML, files-only) | CLI tools must be composable in scripts and agent workflows | LOW | Already implemented |
| Collection scoping (`-c` / `--collection`) | Users want to search specific vaults, not everything every time | LOW | Already implemented |
| Result limiting (`-n`) | Control result volume for different use cases | LOW | Already implemented |
| MCP server integration | AI assistants expect tools to expose search via MCP | MEDIUM | Skeleton exists; needs unification and full implementation |
| Local-first execution | Privacy expectation for personal notes; no forced cloud | LOW | Core design constraint; needs local model support |

### Differentiators (Competitive Advantage)

Features that set qmd apart from simple ripgrep or basic FTS search.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| LLM reranking | Reorders fused results for best relevance; the "secret sauce" of `qmd query` | HIGH | Missing; requires local GGUF reranker integration |
| LLM query expansion | Expands vague queries into lex/vec/hyde variants to improve recall | HIGH | Missing; requires local query-expansion model |
| Query document format (`lex:`, `vec:`, `hyde:`, `expand:`) | Power users can compose multi-modal queries for complex retrieval | MEDIUM | Missing entirely; unique qmd feature |
| Intent parameter (`--intent`) | Disambiguates ambiguous queries across all pipeline stages | MEDIUM | Missing; added in qmd v1.1.5 |
| Score explainability (`--explain`) | Shows trace of BM25, RRF, reranker, and final blended scores | LOW | Missing; added in qmd v1.1.2 |
| Candidate limit tuning (`--candidate-limit` / `-C`) | Controls reranker input size for latency/quality tradeoffs | LOW | Missing; added in qmd v1.1.2 |
| Strong-signal bypass | Skips heavy pipeline when BM25 already has an obvious match | LOW | Could be ported; mainly a latency optimization |
| Smart snippet extraction | Extracts intent-aware lines from chunks with weighted term scoring | MEDIUM | Missing; requires implementing snippet engine |
| Context descriptions (`qmd context add`) | Human-written collection summaries improve retrieval quality | LOW | Missing; helps agent and hybrid search |
| Pre-update shell commands (`update-cmd`) | Auto-run `git pull` before indexing for synced knowledge bases | LOW | Missing; useful for developer workflows |
| Search benchmarking (`qmd bench`) | Measures precision@k, recall, MRR, F1 across backends | MEDIUM | Missing; useful for tuning search quality |
| Per-collection model configuration | Different collections can use different embed/rerank models | MEDIUM | Missing; added in qmd v2.1.0 |
| Min-score threshold (`--min-score`) | Filters low-confidence results, critical for agent integrations | LOW | Missing |
| Full-content retrieval (`--full`) | Return entire document instead of snippets | LOW | Missing |
| Line-number output (`--line-numbers`) | Anchors results to specific lines for developer workflows | LOW | Missing |
| Virtual file tree (`qmd ls`) | Inspect indexed collections without touching disk | LOW | Missing |
| DocID-based retrieval (`#abc123`) | Stable content-hash references survive renames | LOW | Missing; useful for agent memory |

### Anti-Features (Deliberately NOT Building)

Features that seem good but create problems for a local CLI search tool.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Web UI | Violates local-first CLI ethos; adds massive complexity (frontend, server, auth) | Stay CLI + MCP only; let the ecosystem build TUIs like `lazyqmd` |
| Real-time collaboration / sync | Out of scope for a single-user local tool; conflicts with local-first model | Let users use Git or Dropbox; provide `update-cmd` hooks |
| Multi-user / permissions system | Personal knowledge base tool has no need for RBAC | Single-user SQLite file with OS-level permissions |
| Complex binary format parsing (PDF, Word, Excel) | Explodes dependency tree and parsing complexity | Focus on Markdown, plain text, and code files only |
| Built-in note editor | Scope creep into becoming an Obsidian competitor | Read-only retrieval; integrate with user's `$EDITOR` |
| Automatic cloud backup | Breaks trust model of local-only tool | Document where the SQLite file lives; let users back it up |
| Plugin architecture for third-party extensions | Premature abstraction; MCP already provides extensibility | Expose clean MCP tools and CLI output formats |
| Real-time file watching / hot reload | Adds daemon complexity, resource usage, and OS-specific edge cases | Explicit `update` command; users control when indexing happens |
| Graph visualization of note links | Cool demo, but not a search feature; adds heavy dependencies | If needed, defer to external tools or Obsidian plugins |
| Built-in LLM chat / RAG answers | Becomes a chatbot instead of a search engine; token costs explode | Return ranked snippets and let the user's agent (Claude, etc.) synthesize |

## Feature Dependencies

```
BM25 Search
    └──requires──> Collection Management
    └──requires──> Document Indexing

Vector Search
    └──requires──> Document Indexing
    └──requires──> Embedding Model Integration

Hybrid Search (RRF)
    └──requires──> BM25 Search
    └──requires──> Vector Search

LLM Reranking
    └──requires──> Hybrid Search
    └──requires──> Local GGUF Reranker Model

Query Expansion
    └──requires──> LLM Query Expansion Model
    └──enhances──> Hybrid Search
    └──enhances──> LLM Reranking

Query Document Format (lex/vec/hyde)
    └──requires──> BM25 Search
    └──requires──> Vector Search
    └──requires──> Hybrid Search Fusion
    └──enhances──> LLM Reranking

Intent Parameter
    └──requires──> Query Expansion
    └──requires──> LLM Reranking
    └──requires──> Snippet Extraction
    └──requires──> Chunk Selection

Snippet Extraction
    └──requires──> Chunking Strategy
    └──requires──> BM25 Search (for term scoring)

Strong-Signal Bypass
    └──requires──> BM25 Search
    └──requires──> Hybrid Search

MCP Server (full)
    └──requires──> Search Pipeline (search / vsearch / query)
    └──requires──> Document Retrieval (get / multi-get)
    └──requires──> Collection Management

Search Benchmarking (bench)
    └──requires──> All Search Backends (BM25, Vector, Hybrid, Full Pipeline)
```

### Dependency Notes

- **Reranking requires Hybrid Search:** The reranker works best when given a diverse candidate set from both lexical and semantic signals.
- **Query Document Format requires both BM25 and Vector:** `lex:` needs BM25, `vec:`/`hyde:` need vector search; they must be fused before reranking.
- **Intent parameter requires the full pipeline:** It affects expansion, reranking, chunk selection, and snippet extraction — all must exist first.
- **MCP server requires stable retrieval APIs:** Agents depend on `get`/`multi-get` and predictable search output schemas.

## MVP Definition

### Launch With (v1)

Minimum viable product — what's needed to validate the concept and achieve functional parity with basic qmd usage.

- [x] **Collection CRUD** — Already exists
- [x] **BM25 search (`docsift search`)** — Already exists
- [x] **Document indexing with checksums** — Already exists
- [ ] **Vector search (`docsift vsearch`)** — Requires fixing stubbed embedder (hard-coded path, random fallback)
- [ ] **Hybrid search (`docsift query`)** — Requires working vector search + RRF; reranking can be deferred
- [ ] **`get` / `multi-get` / `ls` commands** — Essential for document retrieval workflows
- [ ] **MCP server unification** — One working MCP server with search and retrieval tools
- [ ] **Configurable embedding models** — Support sentence-transformers and local GGUF via llama-cpp-python
- [ ] **JSON / structured output stability** — Agents depend on predictable schemas

### Add After Validation (v1.x)

Features to add once core search and retrieval are solid.

- [ ] **LLM reranking** — The main quality differentiator for `docsift query`
- [ ] **LLM query expansion** — Improves recall for vague queries
- [ ] **Query document format (`lex:`, `vec:`, `hyde:`, `expand:`)** — Power-user feature
- [ ] **Score explainability (`--explain`)** — Useful for debugging and tuning
- [ ] **Min-score threshold (`--min-score`)** — Critical for agent reliability
- [ ] **Full-content and line-number output** — Developer experience improvements
- [ ] **Context descriptions (`context add`)** — Improves retrieval for agent use cases
- [ ] **Pre-update commands (`update-cmd`)** — Developer workflow convenience

### Future Consideration (v2+)

Features to defer until the tool is proven and stable.

- [ ] **Search benchmarking (`bench`)** — Nice for tuning, but not essential
- [ ] **Per-collection model configuration** — Advanced optimization
- [ ] **DocID-based stable references** — Useful but requires content-addressable hashing
- [ ] **Strong-signal bypass** — Performance optimization, not correctness
- [ ] **Intent parameter** — Requires the full pipeline to be mature first
- [ ] **Smart snippet extraction with intent weighting** — Polishing feature

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Fix stubbed embedder | HIGH | LOW | P1 |
| Implement `get` / `multi-get` / `ls` | HIGH | LOW | P1 |
| Unify MCP server | HIGH | MEDIUM | P1 |
| Configurable embedding models | HIGH | MEDIUM | P1 |
| LLM reranking | HIGH | HIGH | P2 |
| LLM query expansion | HIGH | HIGH | P2 |
| Query document format | MEDIUM | MEDIUM | P2 |
| `--explain` | MEDIUM | LOW | P2 |
| `--min-score` | MEDIUM | LOW | P2 |
| Context descriptions | MEDIUM | LOW | P2 |
| `update-cmd` | LOW | LOW | P2 |
| `--candidate-limit` | LOW | LOW | P3 |
| `bench` | LOW | MEDIUM | P3 |
| Intent parameter | MEDIUM | HIGH | P3 |
| Per-collection models | LOW | MEDIUM | P3 |

**Priority key:**
- P1: Must have for launch (functional parity with basic qmd)
- P2: Should have, add when core is solid (qmd quality differentiation)
- P3: Nice to have, future consideration

## Competitor Feature Analysis

| Feature | qmd (TypeScript) | ripgrep | Obsidian Search | Our Approach (docsift) |
|---------|------------------|---------|-----------------|------------------------|
| BM25 keyword search | Yes | No (regex only) | Yes | Yes (FTS5) |
| Vector semantic search | Yes | No | Via plugins | Yes (planned) |
| Hybrid search + reranking | Yes | No | Via plugins | Yes (planned) |
| Local-only / no cloud | Yes | Yes | Yes | Yes (core constraint) |
| CLI composability | Yes | Yes | Limited | Yes (multiple output formats) |
| MCP server | Yes | No | No | Yes (in progress) |
| Query document syntax | Yes | No | No | Planned (P2) |
| Intent parameter | Yes | No | No | Planned (P3) |
| Speed (large vaults) | Fast (indexed) | Very fast | Fast (indexed) | Target: ripgrep-level for BM25 |
| Mobile support | No | No | Yes | No (out of scope) |
| Web UI | No | No | Yes | No (anti-feature) |

## Sources

- [tobi/qmd on GitHub](https://github.com/tobi/qmd)
- [QMD Changelog](https://github.com/tobi/qmd/blob/main/CHANGELOG.md)
- [QMD Query Syntax Documentation](https://mintlify.com/tobi/qmd/concepts/query-syntax)
- [QMD MCP Query Tool Docs](https://mintlify.com/tobi/qmd/mcp/query)
- [Introducing lazyqmd: a tui for QMD](https://alexanderzeitler.com/articles/introducing-lazyqmd-a-tui-for-qmd/)
- [qmd for faster Obsidian search](https://rizwan.dev/blog/qmd-for-faster-obsidian-search/)
- [12 Common Personal Knowledge Management Mistakes](https://www.dsebastien.net/12-common-personal-knowledge-mistakes-and-how-to-avoid-them/)
- [Obsidian search vs ripgrep vs vector search comparison](https://forum.obsidian.md/t/how-do-you-increase-the-ease-of-finding-commonly-accessed-notes/58207)
- [Burnt Sushi ripgrep blog post](https://blog.burntsushi.net/ripgrep/)
- [QMD: Local Semantic Search That Cuts AI Agent Token Costs by 90%](https://www.heyuan110.com/posts/ai/2026-03-25-qmd-local-search-ai-agent-memory/)

---
*Feature research for: docsift (local markdown document search engine)*
*Researched: 2026-04-14*
