# API Coverage — OpenAI-compatible Embeddings API

> Full coverage by default. Opt-outs are explicit, reasoned decisions.

**Detector:** `api-coverage.cjs` returned `detected: true` over the Phase 03 scope. The integration is the
VEC-01 gap identified in `03-VERIFICATION.md`: the OpenAI-compatible API embedding backend, addressed
through the `openai` Python SDK (`client.embeddings.*`). This matrix covers the second integration
against the embedding capability (local backends shipped in the original phase; this is the remote
variant) and re-decides every capability from the full-coverage baseline.

| capability | decision | reason |
|---|---|---|
| embeddings.create — single-text input | INTEGRATE | `OpenAIEmbedder.embed()` — core VEC-01 deliverable |
| embeddings.create — batched input array | INTEGRATE | `OpenAIEmbedder.embed_batch()` slices inputs at `batch_size` and concatenates ordered results |
| embeddings.create — `dimensions` parameter (Matryoshka truncation) | OPT-OUT | many OpenAI-compatible endpoints ignore or reject `dimensions` (03-RESEARCH.md A2); SIF uses the endpoint's native dimension via auto-detection + local cache (03-CONTEXT.md D-05) instead |
| dimension auto-detection (single probe + local cache) | INTEGRATE | locked decision D-05 — first load probes with a minimal input, caches to `openai_dim_cache.json` (7-day TTL) |
| base_url override (generic OpenAI-compatible endpoints) | INTEGRATE | locked decision D-04 — `api_base` flows Settings → factory kwargs → `OpenAI(base_url=...)`, addressing `{api_base}/embeddings` |
| model listing (GET /models) | OPT-OUT | not needed — an invalid `SIF_MODEL_NAME` surfaces as an explicit error on the first embed call |
| per-request `user` attribution | OPT-OUT | single-user local tool; no abuse tracking to attribute |
| `encoding_format=base64` | OPT-OUT | transport optimization only; default float decoding is used, no capability lost |
| streaming embeddings | OPT-OUT | not offered by the embeddings endpoint — N/A by API design |

Every `OPT-OUT` carries a reason. The matrix is decided at plan time (gap-closure plan `03-07-PLAN.md`); the seal-time `api-coverage.verify-pre` gate validates it.
