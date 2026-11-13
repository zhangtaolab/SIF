# API Coverage — external services in Phase 17

> Full coverage by default. Opt-outs are explicit, reasoned decisions.
> Scope: PyPI/TestPyPI trusted publishing, GitHub Actions/API, PyPI verification APIs, and hc remote execution.

| capability | decision | reason |
|---|---|---|
| PyPI trusted-publishing upload (OIDC, `pypa/gh-action-pypi-publish@release/v1`) | INTEGRATE | ENG-03 — the release path itself; job-scoped `id-token: write`, environment `pypi` (plan 17-05). |
| TestPyPI trusted-publishing upload (pending publisher, `skip-existing`) | INTEGRATE | ENG-03 — required dry run before PyPI (plans 17-05, 17-07). |
| PEP 740 attestation generation (trusted-publishing default) | INTEGRATE | ENG-03 — attestations must be present on the published artifact. |
| PEP 740 attestation verification (`pypi-attestations verify pypi`) | INTEGRATE | ENG-03 acceptance — verifies provenance against repository zhangtaolab/sif (plan 17-07). |
| PyPI JSON API (`/pypi/docsif/1.1.2/json`) | INTEGRATE | Verifies published version and that the mcp-name marker reached `info.description` (plan 17-07). |
| PyPI publisher registration (project/TestPyPI UI) | OPT-OUT | No public API exists; maintainer-only UI action handled as a blocking `checkpoint:human-action` in plan 17-06. |
| GitHub Actions workflow execution (test matrix, publish) | INTEGRATE | ENG-01/ENG-03 — the regression net and release pipeline run there (plans 17-03, 17-05). |
| GitHub Actions artifact transfer (`upload-artifact`/`download-artifact`) | INTEGRATE | Build-once, publish-same-bytes (plan 17-05). |
| GitHub REST API via `gh` (environments create/read, run list/view/logs) | INTEGRATE | Environment creation and CI evidence gates (plans 17-03, 17-06, 17-07). |
| GitHub Actions runner images (ubuntu-latest, macos-latest) | INTEGRATE | The 8-cell matrix topology (D-01/D-03). |
| hc remote execution on yoga (`hc exec --on yoga`) | INTEGRATE | ENG-02 — the Windows degradation smoke is run on demand via the `windows-smoke` target (plan 17-04). |
| uv-managed Python installation (`uv python install`) on runners and yoga | INTEGRATE | Required on runners and on yoga (no usable system Python there). |
| `uvx` ephemeral tools (`twine`, `pypi-attestations`) | INTEGRATE | Build metadata check and attestation verification; never project dependencies. |
| GitHub Release creation API (`gh release create`) | OPT-OUT | Not needed — the tag plus PyPI release is the deliverable; no GitHub Release object is part of ENG-03. |
| MCP Registry API / `mcp-publisher` | OPT-OUT | Explicitly Phase 22 (MCP-09); Phase 17 only publishes the README marker it consumes. |
| PyPI yank/delete APIs | OPT-OUT | Yanking is explicitly not a retry mechanism (D-13 one-way decision); a failed version gets a new patch release. |
| TestPyPI/PyPI dependency mirroring | OPT-OUT | TestPyPI does not mirror dependencies; install proofs add the PyPI extra index as documented (plan 17-07). |

**Detector note:** the deterministic `api-coverage` probe fired on the phrase "PyPI Integrity API" in the plan bodies. The matrix above is the reasoned capability decision for every external service this phase actually touches; nothing in the phase integrates an application API/SDK beyond these release and CI services.
