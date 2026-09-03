# Deferred Items — Phase 03 (out-of-scope discoveries)

## 2026-09-03 — plan 03-07 execution

- **mypy cannot run in this environment (pre-existing).** `mypy src/sif` dies inside
  `site-packages/sentence_transformers/base/modality.py` ("Pattern matching is only
  supported in Python 3.10 and greater") because the project pins
  `python_version = 3.9` in pyproject `[tool.mypy]` while the installed
  sentence-transformers 5.4.1 uses 3.10+ syntax. With `--follow-imports=skip`,
  mypy reports "Class cannot subclass Embedder" / "Returning Any" against
  pre-existing classes (SentenceTransformerEmbedder, LlamaCppEmbedder,
  ModelScopeEmbedder) untouched by plan 03-07. Not caused by this plan; the
  mandated CLAUDE.md quality suite (ruff check, ruff format --check, pytest) is
  green. Fix suggestion: raise `[tool.mypy] python_version` to >=3.10 or add
  mypy overrides ignoring sentence_transformers.
