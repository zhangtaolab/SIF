---
name: docsift-get
description: "Retrieve document content from DocSift index by path, ID, or pattern"
argument-hint: "<path_or_pattern> [--lines N] [--from-line M]"
allowed-tools:
  - Bash
---

<objective>
Retrieve document content from the user's DocSift index.

Supports single document by path or document ID.
Supports batch retrieval via glob patterns or comma-separated paths.
Returns structured JSON with path and content for each document.

Requires docsift CLI to be installed and available in PATH.
</objective>

<process>

1. **Determine retrieval mode**
   - If pattern contains `*` or `?`: use `multi-get`
   - If pattern contains commas: use `multi-get`
   - Otherwise: use single `get`

2. **Build the CLI command** with smart defaults:
   - Always include: `-q --json` (quiet + JSON output)
   - Default: `--line-numbers`
   - LLM can override defaults via arguments

3. **Execute via subprocess**:

   **Single document by path:**
   ```bash
   docsift get get -q --json --line-numbers "{path}"
   ```

   **Single document by ID:**
   ```bash
   docsift get get -q --json --line-numbers "{doc_id}"
   ```

   **Limited lines:**
   ```bash
   docsift get get -q --json --line-numbers --lines 50 "{path}"
   ```

   **From specific line:**
   ```bash
   docsift get get -q --json --line-numbers --from-line 10 --lines 20 "{path}"
   ```

   **Batch retrieval (glob pattern):**
   ```bash
   docsift get multi-get -q --json --line-numbers "{pattern}"
   ```

   **Batch retrieval (comma-separated):**
   ```bash
   docsift get multi-get -q --json --line-numbers "{path1},{path2},{path3}"
   ```

4. **Parse and return JSON output**
   - Single get: return JSON object with path and content
   - Multi-get: return JSON array, each element has path and content
   - LLM formats the results for the user

5. **Error handling**
   - If return code != 0: return stderr content to LLM for interpretation
   - If document not found: stderr will indicate — let LLM explain to user
   - If no index exists: note user needs to run `docsift update` first

</process>

<example>

User: "Read my notes/python.md file"
→ docsift get get -q --json --line-numbers "notes/python.md"

User: "Show first 30 lines of README.md"
→ docsift get get -q --json --line-numbers --lines 30 "README.md"

User: "Get all markdown files in the notes folder"
→ docsift get multi-get -q --json --line-numbers "notes/*.md"

User: "Read README and CONTRIBUTING"
→ docsift get multi-get -q --json --line-numbers "README.md,CONTRIBUTING.md"

</example>
