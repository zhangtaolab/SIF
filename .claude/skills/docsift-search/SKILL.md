---
name: docsift-search
description: "Search documents in DocSift index using BM25, vector, or hybrid search"
argument-hint: "<query> [--strategy query|search|vsearch] [--collection NAME] [--limit N] [--all]"
allowed-tools:
  - Bash
---

<objective>
Search the user's DocSift document index using natural language queries.

Default strategy is hybrid search (query = BM25 + Vector + RRF) for best results.
Can explicitly switch to BM25 only (search) or vector only (vsearch).
Returns structured JSON results with path, score, and snippet.

Requires docsift CLI to be installed and available in PATH.
</objective>

<process>

1. **Determine search strategy** (default: hybrid)
   - If user specifies `--strategy search`: use BM25
   - If user specifies `--strategy vsearch`: use vector search
   - Otherwise: use hybrid search (`docsift search query`)

2. **Build the CLI command** with smart defaults:
   - Always include: `-q --json` (quiet + JSON output)
   - Default: `--limit 10 --line-numbers`
   - LLM can override defaults via arguments

3. **Execute via subprocess**:

   **Hybrid search (default):**
   ```bash
   docsift search query -q --json --limit 10 --line-numbers "{query}"
   ```

   **BM25 only:**
   ```bash
   docsift search search -q --json --limit 10 --line-numbers "{query}"
   ```

   **Vector only:**
   ```bash
   docsift search vsearch -q --json --limit 10 --line-numbers "{query}"
   ```

   **With collection filter:**
   ```bash
   docsift search query -q --json --limit 10 --line-numbers -c "{collection}" "{query}"
   ```

   **Search all collections:**
   ```bash
   docsift search query -q --json --limit 10 --line-numbers --all "{query}"
   ```

4. **Parse and return JSON output**
   - Return the raw JSON array to the LLM
   - Each result contains: path, score, snippet, highlights
   - LLM formats the results for the user

5. **Error handling**
   - If return code != 0: return stderr content to LLM for interpretation
   - If output is `[]`: report "No results found"
   - If stderr contains "No index found": note user needs to run `docsift update` first

</process>

<example>

User: "Find notes about Python asyncio"
→ docsift search query -q --json --limit 10 --line-numbers "Python asyncio"

User: "Search for 'machine learning' using BM25 only"
→ docsift search search -q --json --limit 10 --line-numbers "machine learning"

User: "Search my notes collection for 'docker' and return top 5"
→ docsift search query -q --json --limit 5 --line-numbers -c notes "docker"

</example>
