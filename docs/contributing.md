<!-- generated-by: gsd-doc-writer -->
# Contributing to SIF

Thank you for your interest in contributing to SIF! This document provides guidelines for contributing to the project.

## Code of Conduct

This project adheres to a code of conduct. By participating, you are expected to:

- Be respectful and inclusive
- Welcome newcomers
- Accept constructive criticism gracefully
- Focus on what's best for the community

## How to Contribute

### Reporting Bugs

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
- Python: [e.g., 3.11.0]
- SIF: [e.g., 1.1.1]

**Logs**
```
Paste relevant logs here
```
```

### Suggesting Features

Feature requests are welcome! Include:

- **Use case**: What problem does it solve?
- **Proposed solution**: How should it work?
- **Alternatives**: What else have you considered?

### Pull Requests

1. **Fork** the repository
2. **Create** a branch (`git checkout -b feature/amazing-feature`)
3. **Commit** changes (`git commit -m 'feat: add amazing feature'`)
4. **Push** to branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

#### PR Checklist

- [ ] Tests pass (`pytest`)
- [ ] Code is formatted (`ruff format .`)
- [ ] Code passes linting (`ruff check .`)
- [ ] Type checking passes (`ty check src/sif`)
- [ ] Documentation updated
- [ ] Reference docs regenerated (`make docs-generate`) if CLI commands or configuration settings changed
- [ ] Changelog updated (docs/changelog.md)
- [ ] Commit messages follow conventions

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
source venv/bin/activate
pip install -e ".[dev]"
```

## Coding Standards

### Python Style

- Follow PEP 8
- Use type hints
- Maximum line length: 100 characters
- Use docstrings for all public functions

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
# Run all tests
pytest

# Run with coverage
pytest --cov=src/sif

# Run specific test
pytest tests/unit/test_collection.py
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

Example:

```python
def search(
    self,
    query: str,
    limit: int = 10,
) -> list[SearchResult]:
    """Search documents matching the query.
    
    Args:
        query: Search query string
        limit: Maximum number of results
        
    Returns:
        List of search results
        
    Raises:
        ValueError: If query is empty
    """
```

### User Documentation

Update relevant documentation when adding features:

- `README.md` - Quick start and overview
- `docs/` - Detailed documentation
- Docstrings - API reference

## Testing Guidelines

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
    # mock_db is a MagicMock standing in for the sqlite3 connection
    pipeline = SearchPipeline(mock_db)

    results = pipeline.search("lex: machine learning")

    assert isinstance(results, list)
    assert all(isinstance(r, SearchResult) for r in results)
```

### Test Coverage

Coverage is collected on every pytest run and the suite fails below 90% total coverage of `src/sif` (see the Troubleshooting section below). Generate the HTML report with:

```bash
pytest --cov=src/sif --cov-report=html
open htmlcov/index.html
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

- Review PRs within a week
- Be constructive in feedback
- Approve when ready
- Merge with appropriate strategy

## Release Process

Maintainers follow this process:

1. Update version in `src/sif/_version.py`
2. Update docs/changelog.md
3. Create git tag
4. Build the distribution (`make build`) and upload it to PyPI
5. Create GitHub release

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

The repository has one GitHub Actions workflow, `.github/workflows/docs.yml` ("Docs Validation"). It is triggered:

- **On pull requests** that touch `docs/**`, `README.md`, `src/sif/cli/**`, `src/sif/config/**`, `scripts/generate_cli_ref.py`, `scripts/generate_config_ref.py`, or `tests/test_docs.py`
- **On pushes** to `main`

The workflow installs the package with `pip install -e ".[dev]"` on Python 3.11, runs `pytest tests/test_docs.py -v --no-cov`, then regenerates the reference docs via `scripts/generate_cli_ref.py` and `scripts/generate_config_ref.py` and fails if `git diff --exit-code docs/cli-reference.md docs/configuration.md` detects drift. In practice:

> If you change CLI commands or configuration settings, regenerate the reference docs and commit the result, or CI will fail:
>
> ```bash
> make docs-generate
> ```

`docs/cli-reference.md` and `docs/configuration.md` are written wholesale by the generation scripts — do not edit them by hand; change the CLI or settings source and rerun `make docs-generate`.

Note: CI does **not** currently run the lint, format, type-check, or test suite — those checks are enforced locally only. Run the full quality suite before opening a PR (see [Coding Standards](#coding-standards) and the Makefile targets below).

## Makefile Targets

The `Makefile` wraps the common development commands:

| Target | What it runs | Notes |
|--------|--------------|-------|
| `make install-dev` | `pip install -e ".[dev]"` + `pre-commit install` | See pre-commit caveat below |
| `make test` | `pytest --cov=src/sif ...` | Coverage is also on by default via `pyproject.toml` `addopts` |
| `make test-fast` | `pytest -x -q` | Coverage still applies via `addopts`; stops at first failure |
| `make docs-test` | `pytest tests/test_docs.py -v --no-cov` | Same docs validation CI runs |
| `make docs-generate` | `scripts/generate_cli_ref.py` + `scripts/generate_config_ref.py` | Regenerate reference docs before committing CLI/config changes |
| `make lint` / `make lint-fix` | `ruff check .` / `ruff check --fix .` | |
| `make format` / `make format-check` | `ruff format .` / `ruff format --check .` | |
| `make typecheck` | `ty check src/sif` | ty is configured in `pyproject.toml` (`[tool.ty]`) |
| `make security` | `bandit -r src/sif -c pyproject.toml` | bandit is not in the `[dev]` extras; install it separately |
| `make all` | lint + typecheck + test | Quick combined check |
| `make ci` | format-check + lint + typecheck + security + test | Full local CI-equivalent run |

`make install-dev`, `make install-all`, and `make pre-commit` invoke the `pre-commit` tool, but no `.pre-commit-config.yaml` is committed to the repository. <!-- VERIFY: make install-dev/install-all/pre-commit reference .pre-commit-config.yaml, which is not in the repository -->

## Questions?

GitHub Discussions is not enabled on this repository. For questions and support, open an issue:

- Issues: [github.com/zhangtaolab/sif/issues](https://github.com/zhangtaolab/sif/issues)

## Recognition

Contributors will be:
- Mentioned in release notes
- Credited in documentation

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Troubleshooting

### Coverage gate fails on partial test runs

`pyproject.toml` enables coverage on every `pytest` invocation (`addopts = "--cov=src/sif ..."` under `[tool.pytest.ini_options]`) and enforces a floor of 90% (`[tool.coverage.report] fail_under = 90`). Running a single test file therefore fails the run even when every test in it passes:

```
FAIL Required test coverage of 90.0% not reached. Total coverage: 12.96%
```

For subset runs during development, disable coverage explicitly:

```bash
pytest --no-cov tests/unit/test_collection.py
```

Before opening a PR, run the full suite (`make test`) so total coverage is measured against the 90% floor — the PR checklist item "Tests pass (`pytest`)" means the full suite with coverage, not a single file.

### Tests fail with ANSI escape codes in assertions

Some terminals and CI harnesses export `FORCE_COLOR`. Rich treats **any non-empty value — including `0` — as forced color**, so CLI output tests fail on plain-text assertions:

```
AssertionError: assert '   1: line1' in '\x1b[1;36ma.md\x1b[0m\n...'
```

Setting `FORCE_COLOR=0` does not help; the variable must be unset. Run the suite with styling suppressed:

```bash
env -u FORCE_COLOR NO_COLOR=1 pytest
```

## Thank You!

Every contribution, no matter how small, helps make SIF better. Thank you for your support!
