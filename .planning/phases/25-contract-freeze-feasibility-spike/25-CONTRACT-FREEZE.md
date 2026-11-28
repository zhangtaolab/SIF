# Phase 25 — Contract Freeze & Feasibility Spike Evidence

> Generated from the authoritative `.planning/phases/25-contract-freeze-feasibility-spike/bench/spike-verdict.json` by
> `.planning/tmp/phase-25/assemble_evidence.py` (D-14). Every numeric value below
> is rendered from the same in-memory dictionary; do not hand-edit this file.

**Decision:** `directional-signal` — mean paired delta > 0 AND helped > hurt

## Freeze anchor

- Tag: `v1.2.5`
- Anchor commit: `6c25e88d99135d82d127ef55a8dd63f81be12197`
- Discussion HEAD: `7c2fb7918a45`
- Freeze-check HEAD (Task 1, manifest capture): `5fb2712d7a9840de22877b13631c93f16e3665ba` — 20 commits since v1.2.5
- Measured final render HEAD: `fb5ac0faee7c3819af2b60092c6c409ce2b7118f` — 21 commits since v1.2.5
  (execution-time `git rev-list --count v1.2.5..HEAD`; CONTEXT's 4 and research's 7 are stale)
- Freeze-check note: freeze-check measurement captured at Task 1 before the evidence commit; the 11 frozen files are untouched by that commit

## Frozen file manifest

START command:

```
shasum -a 256 pyproject.toml uv.lock tests/unit/mcp/test_wire_transcripts.py \
  tests/unit/mcp/test_packaging.py src/sif/mcp/protocol.py src/sif/mcp/tools.py \
  tests/unit/mcp/goldens/*.json
```

START manifest (11 lines):

```
6fa950c66a6a44f6bb16209048a10321ef09966ac20b9aee06ba3af8bc225690  pyproject.toml
b0175d451e4f8c127da90ffeef94d049a5f181d36743076eaae42b102ea5a308  uv.lock
221c8a68fdf639d4b46e5b0df2fd4b0930b5aa5756c0b71307e0eccc2afd5854  tests/unit/mcp/test_wire_transcripts.py
b5f08b4d5f0b3405784c880e741989250ff5eaef9a8d6535913698ed6319e5a7  tests/unit/mcp/test_packaging.py
00312cb082fec485b40fcaade9fc035eb65a2c8a092f9122b33ea1b5087c4638  src/sif/mcp/protocol.py
70c1e306dd2c191a929ac011458f6a60cf1146b26705e53c565852b7a9082921  src/sif/mcp/tools.py
1c425585808515b466cc261223cefa1cd36602bcd27b46510d2ea0289d353b7a  tests/unit/mcp/goldens/2024-11-05.json
395a3750876f79b5dac8bc359314038669ecffa11db06cb20f469a9d8dc8ff93  tests/unit/mcp/goldens/2025-03-26.json
608a563ce1a5ee997787170e8e09ae75e441c62eef00e03806962e548cba700f  tests/unit/mcp/goldens/2025-06-18.json
b96fb5cba5e54cedcb154c335ee4e88e97af5e950a402ecdeb21ab82d370d806  tests/unit/mcp/goldens/2025-11-25.json
1246e23c1d9580bc8d0c18a7641a27dadfeb9781115a0b879103dc0d3ed8cec5  tests/unit/mcp/goldens/2026-07-28.json
```

END command: identical to the START command.

END manifest (11 lines):

```
6fa950c66a6a44f6bb16209048a10321ef09966ac20b9aee06ba3af8bc225690  pyproject.toml
b0175d451e4f8c127da90ffeef94d049a5f181d36743076eaae42b102ea5a308  uv.lock
221c8a68fdf639d4b46e5b0df2fd4b0930b5aa5756c0b71307e0eccc2afd5854  tests/unit/mcp/test_wire_transcripts.py
b5f08b4d5f0b3405784c880e741989250ff5eaef9a8d6535913698ed6319e5a7  tests/unit/mcp/test_packaging.py
00312cb082fec485b40fcaade9fc035eb65a2c8a092f9122b33ea1b5087c4638  src/sif/mcp/protocol.py
70c1e306dd2c191a929ac011458f6a60cf1146b26705e53c565852b7a9082921  src/sif/mcp/tools.py
1c425585808515b466cc261223cefa1cd36602bcd27b46510d2ea0289d353b7a  tests/unit/mcp/goldens/2024-11-05.json
395a3750876f79b5dac8bc359314038669ecffa11db06cb20f469a9d8dc8ff93  tests/unit/mcp/goldens/2025-03-26.json
608a563ce1a5ee997787170e8e09ae75e441c62eef00e03806962e548cba700f  tests/unit/mcp/goldens/2025-06-18.json
b96fb5cba5e54cedcb154c335ee4e88e97af5e950a402ecdeb21ab82d370d806  tests/unit/mcp/goldens/2025-11-25.json
1246e23c1d9580bc8d0c18a7641a27dadfeb9781115a0b879103dc0d3ed8cec5  tests/unit/mcp/goldens/2026-07-28.json
```

- START == END: **true** (byte-identical; `diff -u` empty)
- Expected-hash comparison against the 25-CONTEXT table: **true** (all 11 entries match)

## Existing test proof

Exact command (the `--no-cov` flag is mandatory; `addopts` enforces `fail_under=90`):

```
.venv/bin/python -m pytest tests/unit/mcp/test_wire_transcripts.py tests/unit/mcp/test_packaging.py -q --no-cov
```

START transcript (exit code 0):

```
exit_code: 0
  See https://docs.pytest.org/en/stable/deprecations.html#callspec2-renamed
    from _pytest.python import CallSpec2

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
13 passed, 1 warning in 0.83s
```

END transcript (exit code 0):

```
exit_code: 0
  Update imports to use CallSpec instead.
  See https://docs.pytest.org/en/stable/deprecations.html#callspec2-renamed
    from _pytest.python import CallSpec2

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
13 passed, 1 warning in 0.58s
```

Both ends report **13 passed**.

## Contract facts

- Tools, exactly seven, in pinned `register_tools()` order:
  `query`, `get`, `multi_get`, `status`, `metadata`, `lex_search`, `vec_search`
- `QueryInput` fields: `query`, `collections`, `limit`, `offset`, `filter`, `per_chunk`, `min_score`, `rrf_k`, `bm25_weight`, `vector_weight`
- `anchor` field present: **false** (CTR-01: no `anchor` request field)
- Wire goldens, exactly 5: `2024-11-05.json`, `2025-03-26.json`, `2025-06-18.json`, `2025-11-25.json`, `2026-07-28.json`
- Runtime dependencies, exactly 13:

1. `click>=8.0.0`
2. `rich>=13.0.0`
3. `python-frontmatter>=1.0.0`
4. `sqlite-vec>=0.1.9`
5. `platformdirs>=3.0.0`
6. `pydantic>=2.0.0`
7. `pydantic-settings>=2.0.0`
8. `fastapi>=0.100.0`
9. `uvicorn>=0.20.0`
10. `watchdog>=4.0.0,<7.0.0`
11. `numpy>=1.24.0`
12. `rapidfuzz>=3.14.5,<4`
13. `mcp>=2.3.0,<3`

- `all` extra entry: `llama-cpp-python>=0.3.35`
- `uv.lock` resolved pin: `0.3.35`

## Compatibility spike (SPK-01)

- Locked version: `0.3.35` → outcome `load-error`
  - Python error type: `ValueError`
  - Error message: `Failed to load model from file: <MODEL_DIR>/LFM3-1.7B-Q4_K_M.gguf`
  - Native llama.cpp reason: `llama_model_load: error loading model: unknown model architecture: 'lfm3'`
- Upgrade version: `0.3.37` → outcome `loaded`
  - Generation non-empty: **true**
  - Generation (verbatim, max_tokens=64):

```
 Write one short sentence about local search. Write one short sentence about local search. Write one short sentence about local search. Write one short sentence about local search. Write one short sentence about local search. Write one short sentence about local search. Write one short sentence about local search. Write one short sentence about local search.
```

- Model: `LFM3-1.7B-Q4_K_M.gguf` — SHA-256 `3793e1e6e2266919d6e015287221b41100175a98eddaba92e111aed3b05c93c4`, size 1099627808 bytes
- Exact commands (sanitized; absolute user paths replaced by placeholders):

```
  <SCRATCH>/venv-locked-0.3.35/bin/python -c import llama_cpp; print(llama_cpp.__version__)
  <SCRATCH>/venv-locked-0.3.35/bin/python -c import llama_cpp; print(llama_cpp.__version__)
  <SCRATCH>/venv-locked-0.3.35/bin/python <SCRATCH>/probe_generate.py --model-path <MODEL_DIR>/LFM3-1.7B-Q4_K_M.gguf --mode generate --out <SCRATCH>/probe-locked.json --n-ctx 2048
  <SCRATCH>/venv-locked-0.3.35/bin/python <SCRATCH>/probe_generate.py --model-path <MODEL_DIR>/LFM3-1.7B-Q4_K_M.gguf --mode generate --out <SCRATCH>/probe-locked-verbose.json --n-ctx 2048 --verbose
  <SCRATCH>/venv-upgrade-0.3.37/bin/python -c import llama_cpp; print(llama_cpp.__version__)
  <SCRATCH>/venv-upgrade-0.3.37/bin/python -c import llama_cpp; print(llama_cpp.__version__)
  <SCRATCH>/venv-upgrade-0.3.37/bin/python <SCRATCH>/probe_generate.py --model-path <MODEL_DIR>/LFM3-1.7B-Q4_K_M.gguf --mode generate --out <SCRATCH>/probe-upgrade.json --n-ctx 2048
  <SCRATCH>/venv-locked-0.3.35/bin/python <SCRATCH>/probe_generate.py --model-path <CROSS_VERSION_GGUF_DIR>/hf_Qwen_Qwen3-Embedding-0.6B-Q8_0.gguf --mode embed --out <SCRATCH>/probe-embed-locked.json --n-ctx 512
  <SCRATCH>/venv-upgrade-0.3.37/bin/python <SCRATCH>/probe_generate.py --model-path <CROSS_VERSION_GGUF_DIR>/hf_Qwen_Qwen3-Embedding-0.6B-Q8_0.gguf --mode embed --out <SCRATCH>/probe-embed-upgrade.json --n-ctx 512
```

- Error stack excerpt:

```
    internals.LlamaModel(
  File "<SCRATCH>/venv-locked-0.3.35/lib/python3.12/site-packages/llama_cpp/_internals.py", line 62, in __init__
    raise ValueError(f"Failed to load model from file: {path_model}")
ValueError: Failed to load model from file: <MODEL_DIR>/LFM3-1.7B-Q4_K_M.gguf
```

- Chat template (verbatim):

```
{{- bos_token -}}
{%- set preserve_thinking = preserve_thinking | default(false) -%}
{%- set enable_thinking = enable_thinking | default(true) -%}

{%- macro render_value(v) -%}
    {%- if v is string -%}
        {{- v -}}
    {%- elif v is boolean -%}
        {{- "true" if v else "false" -}}
    {%- elif v is none -%}
        {{- "null" -}}
    {%- elif v is mapping or (v is sequence and v is not string) -%}
        {{- v | tojson -}}
    {%- else -%}
        {{- v -}}
    {%- endif -%}
{%- endmacro -%}

{%- macro parse_content(content) -%}
    {%- if content is string -%}
        {{- content -}}
    {%- elif content is mapping and content.get("type") == "image" -%}
        {{- "<|vision_start|><|image|><|vision_end|>" -}}
    {%- elif content is mapping and content.get("type") == "video" -%}
        {{- "<|vision_start|><|video|><|vision_end|>" -}}
    {%- elif content is mapping and content.get("type") == "text" -%}
        {{- (content.get("text") or "") | string -}}
    {%- elif content is mapping -%}
        {{- content | tojson -}}
    {%- elif content is iterable -%}
        {%- set _ns = namespace(result="") -%}
        {%- for item in content -%}
            {%- if item is string -%}
                {%- set _ns.result = _ns.result + item -%}
            {%- elif item is mapping and item.get("type") == "image" -%}
                {%- set _ns.result = _ns.result + "<|vision_start|><|image|><|vision_end|>" -%}
            {%- elif item is mapping and item.get("type") == "video" -%}
                {%- set _ns.result = _ns.result + "<|vision_start|><|video|><|vision_end|>" -%}
            {%- elif item is mapping and item.get("type") == "text" -%}
                {%- set _ns.result = _ns.result + ((item.get("text") or "") | string) -%}
            {%- else -%}
                {%- set _ns.result = _ns.result + (item | tojson) -%}
            {%- endif -%}
        {%- endfor -%}
        {{- _ns.result -}}
    {%- elif content is not none -%}
        {{- content | tojson -}}
    {%- endif -%}
{%- endmacro -%}

{%- macro render_tool_calls(tool_calls) -%}
    {%- for tool_call in tool_calls -%}
        {%- if not loop.first -%}{{- "\n\n" -}}{%- endif -%}
        {%- set func = tool_call["function"] if "function" in tool_call else tool_call -%}
        {%- set func_args = func.get("arguments") -%}
        {%- if func_args is string and (func_args | trim) not in ["", "{}", "null"] -%}
            {{- raise_exception("Tool call arguments must be a mapping, got a JSON-encoded string: parse arguments with json.loads() before applying the chat template") -}}
        {%- endif -%}
        {{- "<tool_call>\n<function=" + func["name"] + ">\n" -}}
        {%- if func_args is mapping -%}
            {%- for arg_name, arg_value in func_args.items() -%}
                {{- "<parameter=" + arg_name + ">\n" + render_value(arg_value) + "\n</parameter>\n" -}}
            {%- endfor -%}
        {%- endif -%}
        {{- "</function>\n</tool_call>" -}}
    {%- endfor -%}
{%- endmacro -%}

{%- macro tool_to_json(tool) -%}
    {%- set fn = tool.function if tool.function is defined else tool -%}
    {%- set ns_t = namespace(first=true) -%}
    {{- "{" -}}
    {%- for k, v in fn.items() -%}
        {%- if k != "defer_loading" -%}
            {%- if not ns_t.first -%}{{- ", " -}}{%- endif -%}
            {%- set ns_t.first = false -%}
            {{- k | tojson -}}{{- ": " -}}{{- v | tojson -}}
        {%- endif -%}
    {%- endfor -%}
    {{- "}" -}}
{%- endmacro -%}

{%- macro is_tool_reference(item) -%}
    {{- "1" if item is mapping and item.get("type") == "tool_reference" else "" -}}
{%- endmacro -%}

{%- macro referenced_tool_to_json(name) -%}
    {%- set _ns = namespace(found=none) -%}
    {%- for tool in tools or [] -%}
        {%- set fn = tool.function if tool.function is defined else tool -%}
        {%- if fn.name == name -%}
            {%- set _ns.found = fn -%}
        {%- endif -%}
    {%- endfor -%}
    {%- if _ns.found is none -%}
        {{- raise_exception("Tool reference '" + name | string + "' not found in available tools. Every tool referenced by a tool_reference must be in `tools` on every request.") -}}
    {%- endif -%}
    {{- tool_to_json(_ns.found) -}}
{%- endmacro -%}

{%- macro render_tool_response(content) -%}
    {%- if content is string and "<tool_response>" in content -%}
        {{- content -}}
    {%- else -%}
    {{- "<tool_response>\n" -}}
    {%- if content is string -%}
        {{- content -}}
    {%- elif content is mapping -%}
        {{- parse_content(content) -}}
    {%- elif content is iterable -%}
        {%- for item in content -%}
            {%- if not loop.first -%}{{- "\n" -}}{%- endif -%}
            {%- if is_tool_reference(item) -%}
                {%- if loop.first or not is_tool_reference(loop.previtem) -%}
                    {{- "<additional_tools>\n" -}}
                {%- endif -%}
                {{- referenced_tool_to_json(item.name) -}}
                {%- if loop.last or not is_tool_reference(loop.nextitem) -%}
                    {{- "\n</additional_tools>" -}}
                {%- endif -%}
            {%- elif item is mapping and item.result is defined and item.result is mapping and item.result.tools is defined -%}
                {{- "<additional_tools>\n" -}}
                {%- set _tl = item.result.tools -%}
                {%- if _tl is string -%}
                    {{- _tl -}}
                {%- elif _tl is mapping -%}
                    {{- tool_to_json(_tl) -}}
                {%- else -%}
                    {%- for t in _tl -%}
                        {%- if not loop.first -%}{{- "\n" -}}{%- endif -%}
                        {{- tool_to_json(t) -}}
                    {%- endfor -%}
                {%- endif -%}
                {{- "\n</additional_tools>" -}}
            {%- else -%}
                {{- parse_content(item) -}}
            {%- endif -%}
        {%- endfor -%}
    {%- elif content is not none -%}
        {{- content | tojson -}}
    {%- endif -%}
    {{- "\n</tool_response>" -}}
    {%- endif -%}
{%- endmacro -%}

{%- set ns = namespace(system_prompt="", last_user_index=-1) -%}
{%- if messages and messages[0]["role"] == "system" -%}
    {%- if messages[0].get("content") -%}
        {%- set ns.system_prompt = parse_content(messages[0]["content"]) -%}
    {%- endif -%}
    {%- set messages = messages[1:] -%}
{%- endif -%}
{%- if tools -%}
    {%- set tools_ns = namespace(lines=[]) -%}
    {%- for tool in tools -%}
        {%- set fn = tool.function if tool.function is defined else tool -%}
        {%- set _dyn = (fn.defer_loading is defined and fn.defer_loading) or (tool.defer_loading is defined and tool.defer_loading) -%}
        {%- if not _dyn -%}
            {%- set tools_ns.lines = tools_ns.lines + [tool_to_json(fn)] -%}
        {%- endif -%}
    {%- endfor -%}
    {%- if tools_ns.lines -%}
        {%- set ns.system_prompt = ns.system_prompt + ("\n\n" if ns.system_prompt else "") + "<tools>\n" + (tools_ns.lines | join("\n")) + "\n</tools>" -%}
    {%- endif -%}
{%- endif -%}
{%- if ns.system_prompt -%}
    {{- "<|im_start|>system\n" + ns.system_prompt + "<|im_end|>\n" -}}
{%- endif -%}
{%- for message in messages -%}
    {%- if message["role"] == "user" -%}
        {%- set ns.last_user_index = loop.index0 -%}
    {%- endif -%}
{%- endfor -%}
{%- set carry = namespace(pending=[]) -%}
{%- for message in messages -%}
    {%- set _next = messages[loop.index0 + 1] if not loop.last else none -%}
    {%- set _merge = message.role == "tool" and not message.get("additional_tools")
        and _next is not none and _next.role == "tool" and not _next.get("additional_tools")
        and message.get("tool_call_id") and _next.get("tool_call_id") == message.get("tool_call_id") -%}
    {%- set _items = [] -%}
    {%- if message.role == "tool" and not message.get("additional_tools") -%}
        {%- set _c = message.get("content") -%}
        {%- if _c is string -%}
            {%- set _items = [{"type": "text", "text": _c}] if _c else [] -%}
        {%- elif _c is mapping -%}
            {%- set _items = [_c] -%}
        {%- elif _c is iterable -%}
            {%- set _items = _c | list -%}
        {%- elif _c is not none -%}
            {%- set _items = [_c] -%}
        {%- endif -%}
    {%- endif -%}
    {%- if _merge -%}
        {%- set carry.pending = carry.pending + _items -%}
    {%- else -%}
    {{- "<|im_start|>" + message.role + "\n" -}}
    {%- if message.role == "assistant" -%}
        {%- generation -%}
        {%- set thinking = message.thinking if message.thinking is defined else message.reasoning if message.reasoning is defined else message.reasoning_content -%}
        {%- set keep_thinking = preserve_thinking or loop.index0 > ns.last_user_index -%}
        {%- if thinking is defined and keep_thinking -%}
            {{- "<think>" + (thinking or "") + "</think>" -}}
        {%- elif keep_thinking and "</think>" not in (message.get("content") if message.get("content") is string else "") -%}
            {{- "<think></think>" -}}
        {%- endif -%}
        {%- set _cfm_tag = "CONTINUE_FINAL_MESSAGE_TAG " -%}
        {%- set _has_cfm = false -%}
        {%- set content = "" -%}
        {%- if message.get("content") -%}
            {%- set content = parse_content(message.content) -%}
        {%- endif -%}
        {%- if not keep_thinking -%}
            {%- if "</think>" in content -%}
                {%- set content = content.split("</think>")[-1] | trim -%}
            {%- endif -%}
            {%- set content = "<think></think>" + content -%}
        {%- endif -%}
        {%- if content.endswith(_cfm_tag) -%}
            {%- set _has_cfm = true -%}
            {%- set _trunc_len = (content | length) - (_cfm_tag | length) -%}
            {%- set content = content[:_trunc_len] -%}
        {%- endif -%}
        {{- content -}}
        {%- if message.tool_calls -%}
            {{- render_tool_calls(message.tool_calls) -}}
        {%- endif -%}
        {%- if _has_cfm -%}
            {{- _cfm_tag -}}
        {%- endif -%}
        {{- "<|im_end|>\n" -}}
        {%- endgeneration -%}
    {%- elif message.role == "tool" -%}
        {%- if message.get("additional_tools") -%}
            {%- set _at = message["additional_tools"] -%}
            {%- if _at is mapping or (_at is sequence and _at is not string) -%}
                {%- set _src = _at -%}
            {%- else -%}
                {%- set _src = message.get("content") -%}
            {%- endif -%}
            {%- if _src is string and "<tool_response>" in _src -%}
                {{- _src -}}
            {%- elif _src is string and "<additional_tools>" in _src -%}
                {{- "<tool_response>\n" + _src + "\n</tool_response>" -}}
            {%- elif _src -%}
                {{- "<tool_response>\n<additional_tools>\n" -}}
                {%- if _src is string -%}
                    {{- _src -}}
                {%- elif _src is mapping -%}
                    {{- tool_to_json(_src) -}}
                {%- else -%}
                    {%- for t in _src -%}
                        {%- if not loop.first -%}{{- "\n" -}}{%- endif -%}
                        {{- tool_to_json(t) -}}
                    {%- endfor -%}
                {%- endif -%}
                {{- "\n</additional_tools>\n</tool_response>" -}}
            {%- endif -%}
        {%- elif carry.pending -%}
            {{- render_tool_response(carry.pending + _items) -}}
            {%- set carry.pending = [] -%}
        {%- else -%}
            {{- render_tool_response("" if message.get("content") is none else message.get("content")) -}}
        {%- endif -%}
        {{- "<|im_end|>\n" -}}
    {%- else %}
        {%- if message.get("content") -%}
            {{- parse_content(message["content"]) -}}
        {%- endif -%}
        {{- "<|im_end|>\n" -}}
    {%- endif %}
    {%- endif -%}
{%- endfor -%}
{%- if add_generation_prompt -%}
    {{- "<|im_start|>assistant\n" -}}
    {%- if enable_thinking -%}
        {{- "<think>" -}}
    {%- else -%}
        {{- "<think></think>" -}}
    {%- endif -%}
{%- endif -%}

```

- Embed/rerank impact: Measured on the cross-version Qwen3-Embedding-0.6B GGUF: both 0.3.35 and 0.3.37 accept embedding=True and return a 1024-dimension .embed() vector (vector length 1 per probe), so the shipped LlamaCppEmbedder / GGUF rerank path is unaffected by the upgrade.
- Embed measurement: dimension 1024, vector length 1, `embedding=True` accepted by both versions.

## Anchor signal spike (SPK-02)

- N: 36 (split `tuning`; `heldout_read`: **false**)
- Fixture: `tests/fixtures/bench/queries.json` — SHA-256 `90a3b0652abe8cfb4d4017d8ea52b5745da5595f8e305d821703570820fefced`
- lex mean nDCG@10: 0.750000
- anchor mean nDCG@10: 0.880203
- Mean paired delta: 0.130203
- helped 6 / hurt 0 / unchanged 30
- Noise floor 1/N: 0.027778
- Rule: mean paired delta > 0 AND helped > hurt
- Decision: `directional-signal`
- Anchor table: `.planning/phases/25-contract-freeze-feasibility-spike/bench/anchor-table.json` — SHA-256 `ea62ffdc5e7afd632c3933c5b715ff901b1fc80c56e81e988ed8c7bfd846acfc`
- Reproducibility: seed 0, rng_used false, rerun_identical true

### Per-query paired table (same rows as the CSV)

| Query | Category | lex nDCG@10 | anchor nDCG@10 | delta | helped | hurt |
|---|---|---|---|---|---|---|
| kelpri protocol | keyword | 1.000000 | 1.000000 | 0.000000 | no | no |
| novbra protocol | keyword | 1.000000 | 1.000000 | 0.000000 | no | no |
| rhusyl protocol | keyword | 1.000000 | 1.000000 | 0.000000 | no | no |
| ambbri protocol | keyword | 1.000000 | 1.000000 | 0.000000 | no | no |
| irkjyn protocol | keyword | 1.000000 | 1.000000 | 0.000000 | no | no |
| qelron protocol | keyword | 1.000000 | 1.000000 | 0.000000 | no | no |
| yanzun protocol | keyword | 1.000000 | 1.000000 | 0.000000 | no | no |
| yolzap protocol | keyword | 1.000000 | 1.000000 | 0.000000 | no | no |
| ivyjor protocol | keyword | 1.000000 | 1.000000 | 0.000000 | no | no |
| navigation route planning | synonym | 0.000000 | 0.000000 | 0.000000 | no | no |
| fermentation culture starter | synonym | 0.000000 | 0.833991 | 0.833991 | yes | no |
| holography light recording | synonym | 0.000000 | 0.517358 | 0.517358 | yes | no |
| cartography mapmaking terrain | synonym | 0.000000 | 0.000000 | 0.000000 | no | no |
| acoustics sound vibration | synonym | 0.000000 | 0.833991 | 0.833991 | yes | no |
| metallurgy metal refining | synonym | 0.000000 | 0.833991 | 0.833991 | yes | no |
| botany plants classification | synonym | 0.000000 | 0.833991 | 0.833991 | yes | no |
| astronomy stars observation | synonym | 0.000000 | 0.000000 | 0.000000 | no | no |
| cryptography encryption secrecy | synonym | 0.000000 | 0.833991 | 0.833991 | yes | no |
| machine learning 机器学习 | multilingual | 1.000000 | 1.000000 | 0.000000 | no | no |
| deep learning 深度学习 | multilingual | 1.000000 | 1.000000 | 0.000000 | no | no |
| neural networks 神经网络 | multilingual | 1.000000 | 1.000000 | 0.000000 | no | no |
| natural language processing 自然语言处理 | multilingual | 1.000000 | 1.000000 | 0.000000 | no | no |
| data mining 数据挖掘 | multilingual | 1.000000 | 1.000000 | 0.000000 | no | no |
| knowledge graphs 知识图谱 | multilingual | 1.000000 | 1.000000 | 0.000000 | no | no |
| cloud computing 云计算 | multilingual | 1.000000 | 1.000000 | 0.000000 | no | no |
| distributed systems 分布式系统 | multilingual | 1.000000 | 1.000000 | 0.000000 | no | no |
| database indexing 数据库索引 | multilingual | 1.000000 | 1.000000 | 0.000000 | no | no |
| flux capacitor charge | rival | 1.000000 | 1.000000 | 0.000000 | no | no |
| warp coil plasma | rival | 1.000000 | 1.000000 | 0.000000 | no | no |
| phase array signal | rival | 1.000000 | 1.000000 | 0.000000 | no | no |
| ion thruster fuel | rival | 1.000000 | 1.000000 | 0.000000 | no | no |
| quantum lattice error | rival | 1.000000 | 1.000000 | 0.000000 | no | no |
| photon sieve light | rival | 1.000000 | 1.000000 | 0.000000 | no | no |
| gravity well trajectory | rival | 1.000000 | 1.000000 | 0.000000 | no | no |
| muon detector particle | rival | 1.000000 | 1.000000 | 0.000000 | no | no |
| tachyon beacon temporal | rival | 1.000000 | 1.000000 | 0.000000 | no | no |

## Working tree (D-16)

`git status --porcelain` at snapshot stage `final`:

```
 M .planning/STATE.md
 M .planning/config.json
 M .planning/phases/25-contract-freeze-feasibility-spike/25-CONTRACT-FREEZE.md
 M .planning/phases/25-contract-freeze-feasibility-spike/bench/spike-verdict.json
 M .planning/state.json
?? .planning/.continue-here.md
?? .planning/HANDOFF.json
?? .planning/v1.3-ui-anchor-milestone-research.md
```

Line-by-line explanation:

- The three whitelisted untracked planning documents are research/handoff material, not this phase's code:
- `.planning/.continue-here.md` — pre-existing research/handoff note; not produced by this phase
- `.planning/HANDOFF.json` — pre-existing handoff manifest; not produced by this phase
- `.planning/v1.3-ui-anchor-milestone-research.md` — pre-existing v1.3 scope research document; not produced by this phase
- Other modified GSD runtime files:
- `.planning/config.json` — GSD runtime config; `_auto_chain_active` is toggled by the orchestrator between waves
- `.planning/state.json` — GSD runtime state; `updated_at` refreshed by a prior session
- `.planning/STATE.md` — session record written by `gsd_run state record-session` (Task 3, final stage only)
- Phase-dir evidence artifacts (`bench/spike-verdict.json`, `bench/spike-delta.csv`, `25-CONTRACT-FREEZE.md`, `COVERAGE.md`) are this phase's committed artifacts; the generator rewrites them and they are committed with the plan.
- `src/`, `tests/`, `pyproject.toml`, and `uv.lock` have **zero** changes: `git diff v1.2.5..HEAD -- pyproject.toml uv.lock src/sif/mcp/ tests/unit/mcp/` is empty and `git status --porcelain` under those paths is empty.

## Reproduction runbook

Phase 25-01 (SPK-01 compatibility proof; throwaway venvs under `<SCRATCH>`):

```
shasum -a 256 pyproject.toml uv.lock tests/unit/mcp/test_wire_transcripts.py \
  tests/unit/mcp/test_packaging.py src/sif/mcp/protocol.py src/sif/mcp/tools.py \
  tests/unit/mcp/goldens/*.json > <SCRATCH>/start-manifest.sha256
.venv/bin/python -m pytest tests/unit/mcp/test_wire_transcripts.py \
  tests/unit/mcp/test_packaging.py -q --no-cov | tee <SCRATCH>/start-tests.txt
<SCRATCH>/venv-locked-0.3.35/bin/python <SCRATCH>/probe_generate.py \
  --model-path <ABS_PATH_TO_LFM3-1.7B-Q4_K_M.gguf> --mode generate \
  --out <SCRATCH>/probe-locked.json --n-ctx 2048
<SCRATCH>/venv-upgrade-0.3.37/bin/python <SCRATCH>/probe_generate.py \
  --model-path <ABS_PATH_TO_LFM3-1.7B-Q4_K_M.gguf> --mode generate \
  --out <SCRATCH>/probe-upgrade.json --n-ctx 2048
.venv/bin/python <SCRATCH>/spike_delta.py
```

Phase 25-02 (contract freeze + evidence assembly):

```
shasum -a 256 pyproject.toml uv.lock tests/unit/mcp/test_wire_transcripts.py \
  tests/unit/mcp/test_packaging.py src/sif/mcp/protocol.py src/sif/mcp/tools.py \
  tests/unit/mcp/goldens/*.json > <SCRATCH>/end-manifest.sha256
diff -u <SCRATCH>/start-manifest.sha256 <SCRATCH>/end-manifest.sha256
.venv/bin/python -m pytest tests/unit/mcp/test_wire_transcripts.py \
  tests/unit/mcp/test_packaging.py -q --no-cov | tee <SCRATCH>/end-tests.txt
git diff --exit-code v1.2.5..HEAD -- pyproject.toml uv.lock src/sif/mcp/ tests/unit/mcp/
.venv/bin/python <SCRATCH>/assemble_evidence.py --stage initial
.venv/bin/python <SCRATCH>/assemble_evidence.py --stage final
```

## Limitations

- The locked 0.3.35 install fell back to the PyPI sdist because the Metal wheel index had no 0.3.35 artifact; 0.3.37 was installed from the Metal wheel index. The exact attempt transcripts are in gitignored scratch.
- The embed/rerank regression was measured on a cross-version Qwen3-Embedding GGUF, not on the LFM3 generation GGUF; both versions accept `embedding=True` and return 1024 dimensions.
- The anchor arm is an RRF fusion design (one BM25 probe per derived anchor) because appending anchors into one FTS string AND-joins tokens and narrows instead of expanding.
- The working-tree `uv.lock` was restored to its committed HEAD content after an out-of-band Aliyun-mirror `uv` rewrite changed it after Wave 1; the restored file hashes to the expected `b0175d45...` value and the committed history has no diff.
- No full pytest suite was run: this phase changes no file under `src/`, `tests/`, `pyproject.toml`, or `uv.lock`, and a full run touches the real model cache (documented Pitfall 7). The plan's reasoned CLAUDE.md waiver applies.
- The direction rule is the literal D-08 rule only; the 0.01 tie rule, bootstrap CI, and held-out gates remain Phase 27 work.
