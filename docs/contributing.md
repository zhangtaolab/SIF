<!-- generated-by: gsd-doc-writer -->
# Contributing to SIF

Thank you for your interest in contributing to SIF! This document provides guidelines for contributing to the project.

## Code of Conduct

The repository does not currently include a `CODE_OF_CONDUCT.md`; this section sets the expectations for participation. By participating, you are expected to:

- Be respectful and inclusive
- Welcome newcomers
- Accept constructive criticism gracefully
- Focus on what's best for the community

## How to Contribute

### Reporting Bugs

The repository has no `.github/ISSUE_TEMPLATE/` directory, so file bugs directly on GitHub Issues using the template below.

Before creating a bug report:

1. Check if the issue already exists
2. Ensure you're using the latest version
3. Try to isolate the problem

When reporting bugs, include:

- **Title**: Clear and descriptive
- **Description**: What happened vs. what you expected
- **Steps to reproduce**: Numbered steps
- **Environment**: OS, Python version, SIF version
- **Logs**: Relevant error messages

**Template:**

```markdown
**Description**
A clear description of the bug.

**To Reproduce**
1. Run '...'
2. Enter '...'
3. See error

**Expected Behavior**
What you expected to happen.

**Environment**
- OS: [e.g., macOS 14.0]
- Python: [e.g., 3.11.0; supported versions are 3.10–3.13]
- SIF: [output of `sif --version`]

**Logs**
```
Paste relevant logs here
```
```

### Suggesting Features

Feature requests are welcome — there is no feature-request issue template, so include the following in a GitHub issue:

- **Use case**: What problem does it solve?
- **Proposed solution**: How should it work?
- **Alternatives**: What else have you considered?

### Pull Requests

1. **Fork** the repository
2. **Create** a branch (`git checkout -b feature/amazing-feature`)
3. **Commit** changes (`git commit -m 'feat: add amazing feature'`)
4. **Push** to branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request against `main`

#### Branch Conventions

- `main` is the default branch and the target for pull requests. A `dev` branch carries in-progress work before it lands on `main`.
- Name feature branches `feature/<short-description>` and bug fix branches `fix/<short-description>`.
- No other branch naming convention is formally documented.

#### PR Checklist

- [ ] Tests pass: the full suite via `pytest` (coverage is enabled by `addopts` and the 90% gate applies; see [Troubleshooting](#troubleshooting))
- [ ] Code is formatted: `ruff format src tests` (`ruff format --check src tests` verifies without rewriting)
- [ ] Linting passes: `ruff check src tests`
- [ ] Type checking passes: `ty check src/sif`
- [ ] Full local check passes: `make ci` (install `bandit` first — it is not in the `[dev]` extras)
- [ ] Documentation updated
- [ ] Reference docs regenerated: `make docs-generate` if CLI commands or configuration settings changed
- [ ] Changelog updated: add an entry under `[Unreleased]` in `docs/changelog.md`
- [ ] Commit messages follow the convention below

#### PR Description Format

There is no `.github/PULL_REQUEST_TEMPLATE.md` in the repository. Use this format for the pull request description:

```markdown
## Description
Brief description of changes.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
How was this tested?

## Checklist
- [ ] Tests pass
- [ ] Code formatted
- [ ] Documentation updated
```

## Development Setup

See [Development Guide](development.md) for detailed setup instructions.

Quick start:

```bash
git clone https://github.com/zhangtaolab/sif.git
cd sif
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e ".[dev]"
```

The distribution is published as `docsif`; the installed command is `sif`. CI uses the committed `uv.lock` — to mirror it locally, run `uv sync --frozen --extra dev --extra embed` and then `uv run --frozen pytest`.

## Coding Standards

### Python Style

- Follow PEP 8 and target Python 3.10+ (use `list[str] | None` union syntax)
- Use type hints; type annotations are checked with `ty check src/sif`
- Maximum line length: 100 characters
- Maximum mccabe complexity: 10
- Use double quotes; ruff isort orders stdlib, third-party, then first-party `sif` with `combine-as-imports = true` and two blank lines after imports
- Use Google-style docstrings for all public functions

### Code Formatting

```bash
# Format code
ruff format .

# Check formatting
ruff format --check .
```

### Linting

```bash
# Lint code
ruff check .

# Fix auto-fixable issues
ruff check --fix .
```

### Type Checking

```bash
ty check src/sif
```

### Testing

```bash
# Run all tests (coverage is collected on every run via addopts)
pytest

# Run a specific test file — add --no-cov while iterating on a subset
pytest --no-cov tests/unit/test_collection.py

# Generate the HTML coverage report
pytest --cov-report=html
```

## Commit Message Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation |
| `style` | Code style (formatting) |
| `refactor` | Code refactoring |
| `perf` | Performance improvement |
| `test` | Tests |
| `chore` | Maintenance |

### Examples

```
feat(search): add query expansion

Add automatic query expansion using word embeddings.
This improves recall for short queries.

Closes #123
```

```
fix(cli): handle missing collection gracefully

Previously, searching a non-existent collection would crash.
Now it shows a helpful error message.

Fixes #456
```

```
docs(readme): update installation instructions

Add instructions for Windows users and conda.
```

## Documentation

### Code Documentation

- All public functions must have docstrings
- Use Google-style docstrings
- Include type information

Example (from `HybridSearcher.search` in `src/sif/search/hybrid.py`):

```python
def search(
    self,
    query: str,
    options: SearchOptions | None = None,
) -> list[SearchResult]:
    """Search using hybrid approach (BM25 + Vector + RRF).

    Args:
        query: Search query
        options: Search options

    Returns:
        Ranked list of search results, raw and unenriched (the pipeline
        exit owns the single context/staleness enrichment).
    """
```

### User Documentation

Update relevant documentation when adding features:

- `README.md` - Quick start and overview
- `docs/` - Detailed documentation
- Docstrings - API reference

## Testing Guidelines

Tests live under `tests/unit/` (area subdirectories plus a few top-level module suites, using mocks or temporary databases) and `tests/integration/` (cross-layer and real-subprocess pipelines); `tests/e2e/` is reserved and currently contains only `__init__.py`. Files are named `test_*.py`, classes `Test*`, and functions `test_*`, as configured under `[tool.pytest.ini_options]`. Shared fixtures and the autouse hermeticity fixtures live in `tests/conftest.py`; see the [Testing Guide](testing.md) for the full suite layout and fixture list.

### Unit Tests

Test individual components in isolation:

```python
def test_collection_creation():
    collection = Collection(id="test", name="test")
    assert collection.name == "test"
```

### Integration Tests

Test component interactions, for example the `SearchPipeline` routing a `lex:`-prefixed query to BM25 search (as in `tests/integration/test_search_pipeline.py`):

```python
def test_bm25_search_pipeline(mock_db):
    # mock_db is a MagicMock standing in for the sqlite3 connection;
    # the BM25 leg is stubbed to return a fixed result
    pipeline = SearchPipeline(mock_db)
    pipeline.hybrid.bm25 = MagicMock(spec=BM25Searcher)
    pipeline.hybrid.bm25.search.return_value = [
        SearchResult(
            document_id="doc-1",
            path="/test.md",
            title="Test",
            collection_name="default",
            score=0.9,
        ),
    ]

    results = pipeline.search("lex: machine learning")

    assert isinstance(results, list)
    assert all(isinstance(r, SearchResult) for r in results)
```

### Test Coverage

Coverage is collected on every pytest run and the suite fails below 90% total coverage of `src/sif` (see the Troubleshooting section below). Generate the HTML report with:

```bash
pytest --cov=src/sif --cov-report=html
# open htmlcov/index.html in a browser
```

## Documentation Contributions

### Fixing Typos

Small fixes can be submitted directly as PRs.

### Major Changes

For significant documentation changes:

1. Open an issue first
2. Discuss the proposed changes
3. Submit PR with clear description

### Documentation Style

- Use clear, concise language
- Include code examples
- Use proper Markdown formatting
- Add diagrams where helpful

## Review Process

### For Contributors

- Respond to review comments promptly
- Make requested changes
- Ask questions if unclear
- Be open to feedback

### For Maintainers

- Review turnaround is not formally documented; maintainers triage pull requests on GitHub
- Be constructive in feedback
- Approve when ready
- Merge with appropriate strategy

## Release Process

Releases are published by the tag-triggered `Publish` workflow; there is no manual build or upload. Maintainers follow this process:

1. **Bump the version.** Update `__version__` in `src/sif/_version.py` — it is the single version literal that packaging, `sif.__version__`, `APP_VERSION`, and the MCP server version all derive from.
2. **Update the changelog.** Add the release section to `docs/changelog.md`.
3. **Run the Windows degradation smoke.** On a clean checkout of the release commit, run `make windows-smoke` against the Windows host (hc remote yoga) and record the tested HEAD the script prints. This is an on-demand, pre-release step — never a per-PR or scheduled job. It requires the `hc` CLI and a synced checkout at `D:\Github\SIF` (override with `YOGA_DIR=...`); `YOGA_PYTHON` defaults to `3.12`.
4. **Commit and confirm the Test Matrix.** Commit the release changes and confirm all eight test cells (Python 3.10–3.13 × ubuntu/macos) plus the lint job are green on that commit.
5. **Tag the release.** Create and push an annotated tag using the `vX.Y[.Z]` form:

   ```bash
   git tag -a v1.1.2 -m "Release version 1.1.2"
   git push origin v1.1.2
   ```

6. **Let the Publish workflow release it.** Pushing the tag triggers `Publish`, which verifies the tag matches `src/sif/_version.py`, builds the distributions once, and publishes them to TestPyPI first and PyPI second through trusted publishing with PEP 740 attestations. A tag that does not exactly equal `v` + the version literal fails the build job before anything is published.

For post-release verification commands (PyPI JSON check, attestation verification, scratch install), see the Release Process section of the [Development Guide](development.md#release-process).

## Areas for Contribution

### Good First Issues

Look for issues labeled:
- `good first issue`
- `help wanted`
- `documentation`

### Feature Areas

- **Search**: New algorithms, improvements
- **Indexing**: Performance, new formats
- **CLI**: New commands, better UX
- **MCP Server**: New tools, transports
- **Documentation**: Tutorials, examples

## Continuous Integration

Three GitHub Actions workflows live in `.github/workflows/`:

### Test Matrix — `test-matrix.yml`

Runs on every push to any branch and on every pull request, with two jobs:

- **Test** — eight cells: Python 3.10, 3.11, 3.12, and 3.13 on both `ubuntu-latest` and `macos-latest`. Each cell installs with `uv sync --frozen --extra dev --extra embed` and runs the full suite via `env -u FORCE_COLOR NO_COLOR=1 uv run --frozen pytest`; the coverage floor applies exactly as it does locally.
- **Lint** — Python 3.12 on `ubuntu-latest`, running `ruff check src tests`, `ruff format --check src tests`, and `ty check src/sif`.

There is no Windows runner in the matrix, and `push: branches: ['**']` means tag pushes do not trigger the Test Matrix — tags go to `Publish`.

All eight test cells plus the lint job must be green on the release commit before it is tagged (see [Release Process](#release-process)). The Test Matrix does not run `bandit`; run `make security` locally if your change touches code the security scan covers.

### Docs Validation — `docs.yml`

Triggered by pushes to `main` and by pull requests that touch `docs/**`, `README.md`, `src/sif/cli/**`, `src/sif/config/**`, `scripts/generate_cli_ref.py`, `scripts/generate_config_ref.py`, or `tests/test_docs.py`. On Python 3.11 it installs `pip install -e ".[dev]"`, runs `pytest tests/test_docs.py -v --no-cov`, then regenerates the reference docs via `scripts/generate_cli_ref.py` and `scripts/generate_config_ref.py` and fails if `git diff --exit-code docs/cli-reference.md docs/configuration.md` detects drift. In practice:

> If you change CLI commands or configuration settings, regenerate the reference docs and commit the result, or CI will fail:
>
> ```bash
> make docs-generate
> ```

`docs/cli-reference.md` and `docs/configuration.md` are written wholesale by the generation scripts — do not edit them by hand; change the CLI or settings source and rerun `make docs-generate`.

### Publish — `publish.yml`

Triggered by pushing a `v*` tag. It verifies that the tag equals `v` + the `src/sif/_version.py` literal, builds the distributions once with `uv build`, runs `twine check` on the artifacts, uploads the `dist` artifact, then publishes to TestPyPI first and PyPI second through GitHub OIDC trusted publishing (the `testpypi` and `pypi` environments) with PEP 740 attestations. No API token or manual upload is involved — see [Release Process](#release-process).

## Makefile Targets

The `Makefile` wraps the common development commands; `make help` lists the common targets, and the `.PHONY` line at the top of the `Makefile` enumerates every declared target (the table below covers the rest):

| Target | What it runs | Notes |
|--------|--------------|-------|
| `make install-dev` | `pip install -e ".[dev]"` | |
| `make test` | `pytest --cov=src/sif ...` | Coverage is also on by default via `pyproject.toml` `addopts` |
| `make test-fast` | `pytest -x -q` | Coverage still applies via `addopts`; stops at first failure |
| `make docs-test` | `pytest tests/test_docs.py -v --no-cov` | The pytest half of Docs Validation in CI; CI also regenerates the reference docs and fails on drift |
| `make docs-generate` | `scripts/generate_cli_ref.py` + `scripts/generate_config_ref.py` | Regenerate reference docs before committing CLI/config changes |
| `make windows-smoke` | `hc exec` on the Windows host (hc remote yoga): prints HEAD, checks the tree is clean, syncs with `uv`, runs `scripts/windows_smoke.py` | On-demand release step only; needs the `hc` CLI and a synced checkout (`YOGA_DIR`, default `D:\Github\SIF`) |
| `make lint` / `make lint-fix` | `ruff check .` / `ruff check --fix .` | |
| `make format` / `make format-check` | `ruff format .` / `ruff format --check .` | |
| `make typecheck` | `ty check src/sif` | ty is configured in `pyproject.toml` (`[tool.ty.src]`, `[tool.ty.environment]`, `[tool.ty.rules]`) |
| `make security` | `bandit -r src/sif -c pyproject.toml` | bandit is not in the `[dev]` extras; install it separately |
| `make all` | lint + typecheck + test | Quick combined check |
| `make ci` | format-check + lint + typecheck + security + test | Full local CI-equivalent run |

## Questions?

For questions and support, open an issue on GitHub:

- Issues: [github.com/zhangtaolab/sif/issues](https://github.com/zhangtaolab/sif/issues)

## Recognition

Contributor authorship is recorded in the repository's commit history and pull requests. Release entries in [docs/changelog.md](changelog.md) describe changes release by release.

## License

SIF is released under the MIT License — see [LICENSE](https://github.com/zhangtaolab/sif/blob/main/LICENSE) for the full text. By contributing, you agree that your contributions will be licensed under the same terms.

## Troubleshooting

### Coverage gate fails on partial test runs

`pyproject.toml` enables coverage on every `pytest` invocation (`addopts = "--cov=src/sif ..."` under `[tool.pytest.ini_options]`) and enforces a floor of 90% (`[tool.coverage.report] fail_under = 90`). Running a single test file therefore fails the run even when every test in it passes:

```
FAIL Required test coverage of 90.0% not reached.
```

For subset runs during development, disable coverage explicitly:

```bash
pytest --no-cov tests/unit/test_collection.py
```

Before opening a PR, run the full suite (`make test`) so total coverage is measured against the 90% floor — the PR checklist item "Tests pass" means the full suite with coverage, not a single file.

### Tests fail with ANSI escape codes in assertions

Some terminals and CI harnesses export `FORCE_COLOR`, and Rich treats **any non-empty value — including `0` — as forced color**. The suite is now color-hermetic: `tests/conftest.py` removes `FORCE_COLOR`, `CLICOLOR_FORCE`, `NO_COLOR`, `PY_COLORS`, and `TTY_COMPATIBLE` at import time — before any `sif.cli` module constructs its Rich consoles — and the autouse `_hermetic_color_env` fixture clears them again before every test, so no shell changes are needed (`tests/unit/cli/test_color_hermeticity.py` pins both properties). The failure and workaround below apply only to pre-fix branches (before commit `6522663`), where CLI output tests failed on plain-text assertions:

```
AssertionError: assert '   1: line1' in '\x1b[1;36ma.md\x1b[0m\n...'
```

Setting `FORCE_COLOR=0` does not help; the variable must be unset. Run the suite with styling suppressed:

```bash
env -u FORCE_COLOR NO_COLOR=1 pytest
```

## Thank You!

Every contribution, no matter how small, helps make SIF better. Thank you for your support!
