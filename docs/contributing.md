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
- SIF: [e.g., 0.1.0]

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
- [ ] Type checking passes (`mypy src/sif`)
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Commit messages follow conventions

#### PR Template

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
git clone https://github.com/sif/sif.git
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
mypy src/sif
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=sif

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

Test component interactions:

```python
def test_index_and_search():
    # Index document
    indexer.index_document(doc)
    
    # Search
    results = searcher.search("query")
    
    # Verify
    assert len(results) > 0
```

### Test Coverage

Aim for high coverage:

```bash
pytest --cov=sif --cov-report=html
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

1. Update version in `_version.py`
2. Update CHANGELOG.md
3. Create git tag
4. Build and upload to PyPI
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

## Questions?

- GitHub Discussions: [github.com/sif/sif/discussions](https://github.com/sif/sif/discussions)
- Issues: [github.com/sif/sif/issues](https://github.com/sif/sif/issues)

## Recognition

Contributors will be:

- Listed in CONTRIBUTORS.md
- Mentioned in release notes
- Credited in documentation

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Thank You!

Every contribution, no matter how small, helps make SIF better. Thank you for your support!
