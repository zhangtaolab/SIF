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

## [0.1.0] - 2024-01-20

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
- Collection listing tool
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
- numpy >= 1.24.0 (optional)

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
pip install --upgrade sif

# Reindex if needed
sif index rebuild --all
```

## Future Roadmap

### 0.2.0 (Planned)
- [ ] Incremental indexing
- [ ] File system watching
- [ ] Web UI
- [ ] Advanced reranking
- [ ] Query suggestions

### 0.3.0 (Planned)
- [ ] Plugin system
- [ ] Multi-language support
- [ ] REST API
- [ ] Distributed search

### 1.0.0 (Planned)
- [ ] Stable API
- [ ] Production-ready
- [ ] Comprehensive test coverage
- [ ] Performance benchmarks

## Contributors

Thanks to all contributors who have helped shape SIF!

- SIF Team

---

[Unreleased]: https://github.com/sif/sif/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/sif/sif/releases/tag/v0.1.0
