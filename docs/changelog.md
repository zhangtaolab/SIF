# Changelog

All notable changes to SIF will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project structure and core modules
- Collection management (create, read, update, delete)
- Document indexing with chunking support
- BM25 full-text search via SQLite FTS5
- Vector semantic search using embeddings
- Hybrid search with RRF fusion
- Query expansion for improved recall
- Result reranking support
- MCP server with stdio and HTTP transports
- CLI with rich formatting
- Comprehensive documentation

### Changed
- N/A

### Deprecated
- N/A

### Removed
- N/A

### Fixed
- N/A

### Security
- N/A

## [1.2.3] - 2026-11-23

### Added
- New machine-to-machine migration guide (`docs/machine-migration.md`) covering index export via `sif index backup`, restore placement, embedder-identity preservation, embedding and model caches, the three source-path relocation routes (same layout, moved root, same-OS prefix rewrite), configuration/MCP/watch recreation, a verification checklist, and troubleshooting; registered in the mkdocs nav and the docs code-block test suite.

## [1.2.2] - 2026-11-19

### Added
- Embedding device detection now auto-selects Intel XPU with CUDA > Intel XPU > Apple MPS > CPU precedence; the typed `_auto_device` helper serves both the sentence-transformers and ModelScope backends, covered by model-free tests and documented in `docs/configuration.md` and `docs/installation.md`.

### Changed
- The release version is now `1.2.2`, still single-sourced in `src/sif/_version.py`.
- The `embed` and `all` extras now declare `torch>=2.11` (minimum supported; 2.14 or newer recommended); `uv.lock` was regenerated with the same resolved torch builds.

### Fixed
- `sif ls` and `sif collection ls` subpath filters now normalize separators on both sides, so POSIX-style subpaths match on Windows and the `collection ls` tree renders POSIX separators on every platform.
- The test suite collects on Windows: the index-locking test guards its `fcntl` import, POSIX-only service, daemon, and signal tests skip on Windows with a stated reason, symlink-dependent tests skip only when the host forbids symlink creation, and permission-bit and Rich-width assertions are platform-honest.

## [1.2.1] - 2026-11-18

### Changed
- The release version is now `1.2.1`, still single-sourced in `src/sif/_version.py`.
- The `embed` and `all` extras now declare `torch>=2.14`; `uv.lock` was regenerated against the unchanged explicit Linux CPU index.

### Fixed
- Sentence-transformers and ModelScope embedder output is renormalized to unit L2 length, so off-unit model output (Qwen3-Embedding norms 0.9985-1.0036) no longer trips the embedding writer's L2-norm gate (#4).
- Embedding-cache rows written by earlier versions are renormalized on read, so upgrading with a populated embeddings cache no longer aborts `sif index embed` (#4).
- Embedders, rerankers, downloads, and `sif models status` now share `<cache>/models/<owner>/<name>`, and the pre-fix v1.2.0 `<cache>/<owner>/<name>` layout migrates automatically (#5).

## [1.2.0] - 2026-11-18

### Changed
- The release version is now `1.2.0`, still single-sourced in `src/sif/_version.py`.
- New runtime dependencies: `mcp>=2.3.0,<3` (official MCP SDK) and `rapidfuzz>=3.14.5,<4` (did-you-mean suggestions).
- Install documentation is now uv-first, with the explicit Linux CPU-torch recipe (`uv tool install --torch-backend=cpu docsif[embed]`).
- Evidence-gated defaults recorded: chunking defaults are unchanged after a tuning sweep on a real corpus, and the optional embed-text breadcrumb overlay ships default-off (`SIF_EMBED_BREADCRUMB=1` to enable).

### Added
- `sif eval` personal search-quality benchmark: held-out splits, replay-stability check, bootstrap noise gate, saved-run `--compare` A/B mode with per-language evidence, and rapidfuzz-backed did-you-mean suggestions.
- Metadata filtering: `--filter` on `search`, `vsearch`, and `query` with the qmd-compatible operator grammar, applied before fusion with a page-escalation notice, plus metadata discovery so agents never guess keys.
- Search correctness: metadata-content checksums with fast metadata-only re-indexing, deterministic pagination (offset) across BM25/vector/hybrid, document-level hybrid dedup with chunk-match annotations, a title-weighted FTS column, and path-context and vector-staleness enrichment on results.
- Index maintenance and safety: `sif index vacuum|backup|cleanup`, embedder identity records that guard against dimension/prompt drift, and a streaming embed writer.
- MCP server rebuilt on the official SDK v2: stdio + HTTP transports with transport-security validation and allowed-host controls, a seven-tool surface with structured output, a detachable `sif mcp` daemon, a Claude Code plugin + marketplace at the repo root, and an MCP Registry manifest.
- Model management: verified model-cache manifests, `sif models pull`, and `sif models status`.

### Fixed
- The canonical metadata serializer persists YAML date values as ISO text instead of raising a latent `TypeError` during checksum hashing.

## [1.1.2] - 2026-11-14

### Changed
- The release version is now `1.1.2`, still single-sourced in `src/sif/_version.py`.
- Dead layers removed: `MigrationManager`, `src/sif/models/search.py`, and `src/sif/search/strategy.py` are gone; their tests and fixtures were deleted with them.
- The phantom `make pre-commit` target and its documentation were removed (no `.pre-commit-config.yaml` exists; `make ci` covers format, lint, type, and tests).
- `black` was dropped from the development dependencies; `ruff format` remains the formatter.
- `torch` is declared directly in the `embed` and `all` extras with a Linux CPU index, so Linux CI resolves CPU torch instead of the multi-GB CUDA stack.
- Added a tag-triggered release workflow that builds once and publishes to TestPyPI then PyPI via trusted publishing (PEP 740 attestations, no API tokens), and added the `<!-- mcp-name: io.github.zhangtaolab/sif -->` marker to the README for MCP Registry ownership.
- The Python 3.13 classifier is now declared after the CI matrix proved green on 3.13.

### Fixed
- `sif watch --detach` and `sif watch --install-service` now refuse on Windows with a clear cause and remedy instead of a raw traceback.
- The index progress spinner stays encodable on legacy Windows consoles (GBK), so `sif index update` no longer crashes on the missing-root warning path.
- `LlamaCppReranker.load()` validates a missing model path before importing `llama_cpp`, raising the documented `ValueError` in environments without the optional dependency.

## [1.1.1] - 2026-11-12

### Changed
- The release version is now single-sourced in `src/sif/_version.py`; packaging, `sif.__version__`, `sif.cli.__version__`, `APP_VERSION`, and the MCP `serverInfo` version all derive from it.

### Fixed
- Install, upgrade, and uninstall instructions and in-app remedy hints now name the published `docsif` distribution.

## [1.0.1] - 2026-11-07

### Fixed
- Install-command typo fix: corrected the extras install command package name (docdocsif to docsif) in README.md and docs (quick task 261107-cdh, commit 2429c09)
- Parser checksum fix: `sif index update` now compares body-hash checksums so unchanged documents are correctly detected and skipped instead of being re-indexed (commit f1f4b30)

## [0.1.0] - 2026-04-15

### Added
- Initial release of SIF
- Core domain entities (Collection, Document, Context)
- Pydantic models for validation
- SQLite repository pattern implementation
- Search strategy pattern with BM25, Vector, and Hybrid implementations
- Reciprocal Rank Fusion (RRF) for result combination
- Embedding model factory supporting Sentence Transformers and GGUF
- CLI with Click framework
- Collection management commands
- Context management commands
- Search commands with multiple output formats
- Index management commands
- MCP server implementation
- Stdio and HTTP transports for MCP
- Configuration via environment variables and .env files
- Comprehensive test suite
- Documentation with MkDocs

### Core Features

#### Collections
- Create, list, show, rename, delete collections
- Add and remove paths from collections
- Track document and chunk counts
- Metadata support

#### Documents
- Index markdown documents
- Automatic chunking with configurable size and overlap
- Checksum-based change detection
- Metadata extraction

#### Search
- BM25 full-text search
- Vector semantic search
- Hybrid search with RRF fusion
- Query expansion
- Result reranking
- Multiple output formats (table, json, csv, md, xml, files)

#### MCP Server
- Stdio transport for local AI assistants
- HTTP transport for remote access
- Search tool
- Document retrieval tool
- Multi-document retrieval tool
- Status tool

#### Configuration
- Environment variable support
- .env file support
- Configurable chunking parameters
- Configurable search parameters
- Configurable logging

### Technical Details

#### Architecture
- Layered architecture (Presentation, Application, Domain, Infrastructure)
- Repository pattern for data access
- Strategy pattern for search algorithms
- Factory pattern for embedding models
- Dependency injection throughout

#### Database Schema
- Collections table
- Documents table
- Chunks table
- Contexts table
- FTS5 virtual table for full-text search
- sqlite-vec for vector storage

#### Dependencies
- click >= 8.0.0
- rich >= 13.0.0
- pydantic >= 2.0.0
- sentence-transformers >= 2.2.0 (optional)
- numpy >= 1.24.0

### Documentation
- README with quick start
- Architecture documentation
- Installation guide
- Configuration reference
- CLI reference
- API reference
- MCP server documentation
- Data models documentation
- Search algorithms documentation
- Development guide
- Contributing guidelines

---

## Release Notes Template

```markdown
## [X.Y.Z] - YYYY-MM-DD

### Added
- New features

### Changed
- Changes to existing functionality

### Deprecated
- Soon-to-be removed features

### Removed
- Removed features

### Fixed
- Bug fixes

### Security
- Security improvements
```

## Version Numbering

SIF follows [Semantic Versioning](https://semver.org/):

- **MAJOR**: Incompatible API changes
- **MINOR**: Backward-compatible functionality additions
- **PATCH**: Backward-compatible bug fixes

### Pre-release Versions

- `0.1.0-alpha.1` - Alpha release
- `0.1.0-beta.1` - Beta release
- `0.1.0-rc.1` - Release candidate

## Upgrading

### From 0.1.0 to 0.2.0

No upgrade steps required for patch releases.

For minor releases:

1. Check CHANGELOG for breaking changes
2. Update configuration if needed
3. Reindex if database schema changed

```bash
# Backup database
cp ~/.local/share/sif/sif.db ~/.local/share/sif/sif.db.backup

# Upgrade package
pip install --upgrade docsif

# Reindex if needed
sif index update
```

## Future Roadmap

### Future
- [ ] Web UI
- [ ] Plugin system
- [ ] Multi-language support
- [ ] REST API
- [ ] Distributed search

## Contributors

Thanks to all contributors who have helped shape SIF!

- SIF Team

---

[Unreleased]: https://github.com/zhangtaolab/sif/compare/v1.2.3...HEAD
[1.2.3]: https://github.com/zhangtaolab/sif/releases/tag/v1.2.3
[0.1.0]: https://github.com/zhangtaolab/sif/releases
[1.2.2]: https://github.com/zhangtaolab/sif/releases/tag/v1.2.2
[1.2.1]: https://github.com/zhangtaolab/sif/releases/tag/v1.2.1
[1.2.0]: https://github.com/zhangtaolab/sif/releases/tag/v1.2.0
[1.1.2]: https://github.com/zhangtaolab/sif/releases/tag/v1.1.2
[1.1.1]: https://github.com/zhangtaolab/sif/compare/v1.0.1...v1.1.2
[1.0.1]: https://github.com/zhangtaolab/sif/releases/tag/v1.0.1
