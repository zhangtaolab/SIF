---
name: sif-search
description: "Search documents in SIF index using BM25, vector, or hybrid search"
argument-hint: "<query> [--strategy query|search|vsearch] [--collection NAME] [--limit N] [--all]"
allowed-tools:
  - Bash
---

<objective>
Search the user's SIF document index using natural language queries.

Default strategy is hybrid search (query = BM25 + Vector + RRF) for best results.
Can explicitly switch to BM25 only (search) or vector only (vsearch).
Returns structured JSON results with path, score, and snippet.

Requires sif CLI to be installed and available in PATH.
</objective>

<process>

1. **Determine search strategy** (default: hybrid)
   - If user specifies `--strategy search`: use BM25
   - If user specifies `--strategy vsearch`: use vector search
   - Otherwise: use hybrid search (`sif search query`)

2. **Build the CLI command** with smart defaults:
   - Always include: `-q` (before subcommand) + `--json` (quiet + JSON output)
   - Default: `--limit 10 --line-numbers`
   - LLM can override defaults via arguments

3. **Execute via subprocess**:

   **Hybrid search (default):**
   ```bash
   sif -q search query --json --limit 10 --line-numbers "{query}"
   ```

   **BM25 only:**
   ```bash
   sif -q search search --json --limit 10 --line-numbers "{query}"
   ```

   **Vector only:**
   ```bash
   sif -q search vsearch --json --limit 10 --line-numbers "{query}"
   ```

   **With collection filter:**
   ```bash
   sif -q search query --json --limit 10 --line-numbers -c "{collection}" "{query}"
   ```

   **Search all collections:**
   ```bash
   sif -q search query --json --limit 10 --line-numbers --all "{query}"
   ```

4. **Parse and return JSON output**
   - Return the raw JSON array to the LLM
   - Each result contains: path, score, snippet, highlights
   - LLM formats the results for the user

5. **Error handling**
   - If return code != 0: return stderr content to LLM for interpretation
   - If output is `[]`: report "No results found"
   - If stderr contains "No index found": note user needs to run `sif update` first

</process>

<example>

User: "Find notes about Python asyncio"
→ sif -q search query --json --limit 10 --line-numbers "Python asyncio"

User: "Search for 'machine learning' using BM25 only"
→ sif -q search search --json --limit 10 --line-numbers "machine learning"

User: "Search my notes collection for 'docker' and return top 5"
→ sif -q search query --json --limit 5 --line-numbers -c notes "docker"

</example>
