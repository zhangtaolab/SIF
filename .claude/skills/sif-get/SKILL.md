---
name: sif-get
description: "Retrieve document content from SIF index by path, ID, or pattern"
argument-hint: "<path_or_pattern> [--lines N] [--from-line M]"
allowed-tools:
  - Bash
---

<objective>
Retrieve document content from the user's SIF index.

Supports single document by path or document ID.
Supports batch retrieval via glob patterns or comma-separated paths.
Returns document content as plain text (first line is the path, followed by content).

Requires sif CLI to be installed and available in PATH.
</objective>

<process>

1. **Determine retrieval mode**
   - If pattern contains `*` or `?`: use `multi-get`
   - If pattern contains commas: use `multi-get`
   - Otherwise: use single `get`

2. **Build the CLI command** with smart defaults:
   - Always include: `-q` (before subcommand, suppresses non-error output)
   - Default: `--line-numbers`
   - LLM can override defaults via arguments

3. **Execute via subprocess**:

   **Single document by path:**
   ```bash
   sif -q get get --line-numbers "{path}"
   ```

   **Single document by ID:**
   ```bash
   sif -q get get --line-numbers "{doc_id}"
   ```

   **Limited lines:**
   ```bash
   sif -q get get --line-numbers --lines 50 "{path}"
   ```

   **From specific line:**
   ```bash
   sif -q get get --line-numbers --from-line 10 --lines 20 "{path}"
   ```

   **Batch retrieval (glob pattern):**
   ```bash
   sif -q get multi-get --line-numbers "{pattern}"
   ```

   **Batch retrieval (comma-separated):**
   ```bash
   sif -q get multi-get --line-numbers "{path1},{path2},{path3}"
   ```

4. **Return output to LLM**
   - Single get: returns path (first line) + content (remaining lines)
   - Multi-get: returns multiple documents separated by headers
   - LLM formats the results for the user

5. **Error handling**
   - If return code != 0: return stderr content to LLM for interpretation
   - If document not found: stderr will indicate — let LLM explain to user
   - If no index exists: note user needs to run `sif update` first

</process>

<example>

User: "Read my notes/python.md file"
→ sif -q get get --line-numbers "notes/python.md"

User: "Show first 30 lines of README.md"
→ sif -q get get --line-numbers --lines 30 "README.md"

User: "Get all markdown files in the notes folder"
→ sif -q get multi-get --line-numbers "notes/*.md"

User: "Read README and CONTRIBUTING"
→ sif -q get multi-get --line-numbers "README.md,CONTRIBUTING.md"

</example>
