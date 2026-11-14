# Deferred Items — Phase 17

Out-of-scope discoveries found during plan execution. Not fixed here.

## From plan 17-08 (documentation sweep)

- `docs/testing.md:81` still lists `factories.py # Test data factories` in the test-suite tree, and `docs/testing.md:146` documents "Test data factories (tests/factories.py)" — `tests/factories.py` was deleted in plan 17-01 and no longer exists.
- `docs/testing.md:99` still lists `test_search.py # Search strategy and response models` under `tests/unit/` — `tests/unit/test_search.py` was deleted in plan 17-01.
- `docs/testing.md:138` still lists the `sample_search_options`, `sample_search_result(s)` fixtures — those fixtures were removed from `tests/conftest.py` in plan 17-01.
- `docs/testing.md:146-157` still documents `SearchOptionsFactory` / `SearchResultFactory` — removed with `tests/factories.py` in plan 17-01.

These are stale test-layout references to deleted test helpers (not the three deleted source layers), outside plan 17-08's enumerated dead-layer literal list and pre-commit scope. A follow-up docs touch-up should reconcile the test-suite layout section in `docs/testing.md` with the current `tests/` tree.
