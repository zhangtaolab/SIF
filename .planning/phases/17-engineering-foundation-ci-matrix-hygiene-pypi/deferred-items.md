# Deferred Items — Phase 17

Out-of-scope discoveries found during plan execution.

## Deferred Items

### From plan 17-08 (documentation sweep) — stale test-layout references in `docs/testing.md`

- **Detail:** `docs/testing.md:81` listed `factories.py # Test data factories` in the test-suite tree, and `docs/testing.md:146` documented "Test data factories (tests/factories.py)" — `tests/factories.py` was deleted in plan 17-01 and no longer exists.
- **Detail:** `docs/testing.md:99` listed `test_search.py # Search strategy and response models` under `tests/unit/` — `tests/unit/test_search.py` was deleted in plan 17-01.
- **Detail:** `docs/testing.md:138` listed the `sample_search_options`, `sample_search_result(s)` fixtures — those fixtures were removed from `tests/conftest.py` in plan 17-01.
- **Detail:** `docs/testing.md:146-157` documented `SearchOptionsFactory` / `SearchResultFactory` — removed with `tests/factories.py` in plan 17-01.
- **Detail:** These were stale test-layout references to deleted test helpers (not the three deleted source layers), outside plan 17-08's enumerated dead-layer literal list and pre-commit scope. A follow-up docs touch-up was to reconcile the test-suite layout section in `docs/testing.md` with the current `tests/` tree.
- **Status:** resolved
- **Resolution:** `docs/testing.md` was regenerated after this entry was filed (commits `f93b04c`, `42e1acd`, `f49458b`; latest 2026-11-18). The current test-suite layout lists neither `tests/factories.py` nor `tests/unit/test_search.py`, and `grep` finds no `sample_search_options`, `sample_search_result(s)`, `SearchOptionsFactory`, or `SearchResultFactory` references; the factory module is mentioned only as removed, and `tests/test_hygiene.py` pins its absence. Verified 2026-11-18 against HEAD of `dev`.
