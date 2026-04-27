# SIF Manual Test Plan

**Test Directory:** `/Users/forrest/SynologyDrive/Obsidian/ScholarCopilot-Dev/raw/markdown`
**Scale:** 307 papers, 266MB
**Use a separate database** to avoid polluting daily index.

## Setup

```bash
export SIF_DB_PATH=/tmp/sif-scholar-test.sqlite
```

## Test 1: Create Collection & Index

```bash
# Create collection
sif collection add /Users/forrest/SynologyDrive/Obsidian/ScholarCopilot-Dev/raw/markdown -n scholar-test -d "学术论文测试集"

# Index (observe speed and output)
sif index update -c scholar-test
```

**Check:** Index completes without errors, shows Added: ~307

---

## Test 2: Collection Stats

```bash
sif collection show scholar-test
sif status
```

**Check:** Documents count is correct (~307), NOT 0

---

## Test 3: Generate Embeddings (Vectorization)

```bash
# Generate vector embeddings for all indexed documents
# Default model: Qwen/Qwen3-Embedding-0.6B (1024 dim, via modelscope)
# This step is slow — expect several minutes for 307 papers
sif index embed -c scholar-test

# (Optional) Force re-embed with a specific model type
# sif index embed -c scholar-test --model-type sentence_transformers --model "all-MiniLM-L6-v2"

# (Optional) Force re-embed all (even already embedded)
# sif index embed -c scholar-test -f
```

**Check:** Embedding completes without errors. Output shows progress and count of embedded chunks.

**Note:** First run will download the model (~1.2GB for Qwen3-Embedding-0.6B). Subsequent runs use cache. If model download fails, try `--model-type sentence_transformers` as fallback.

---

## Test 4: Verify Vector Index

```bash
# Check chunks were created
sif collection show scholar-test

# Status should show Chunks > 0
sif status
```

**Check:** Chunks count > 0, indicating vectors were stored in sqlite-vec

---

## Test 5: Vector Search

```bash
# Pure vector similarity search
sif search vsearch "how does chromosome folding affect gene regulation"

# Another semantic query (no exact keyword match needed)
sif search vsearch "methods for detecting drug side effects in children"

# With limit and JSON output
sif search vsearch "immune system antibody response" -n 5 --json | python -m json.tool | head -30
```

**Check:** Returns semantically relevant papers even without exact keyword overlap. Scores and results differ from BM25 (Test 7).

---

## Test 6: Hybrid Search (BM25 + Vector + RRF)

```bash
# Hybrid search combines BM25 and vector via Reciprocal Rank Fusion
sif search query "gene expression regulation"

# Compare with pure BM25
sif search search "gene expression regulation"

# Compare with pure vector
sif search vsearch "gene expression regulation"

# Hybrid with explain to see score breakdown
sif search query "gene expression regulation" --explain -n 3
```

**Check:** Hybrid results should rank differently from pure BM25 or pure vector. `--explain` shows BM25 score, vector score, and final RRF fused score.

---

## Test 8: Get by Filename

```bash
# Short filename (PMID number)
sif get get 30522467.md

# Another one
sif get get 11847345.md
```

**Check:** Can retrieve paper content via short filename

---

## Test 9: BM25 Keyword Search

```bash
# English keywords
sif search search "chromosome conformation"

# Medical keywords
sif search search "poisoning paediatric"

# Cross-domain
sif search search "antibody immune"
```

**Check:** Returns relevant papers, scores reasonable, highlights meaningful

---

## Test 10: Search Output Formats

```bash
# JSON
sif search search "chromosome" --json | python -m json.tool | head -20

# CSV
sif search search "chromosome" --csv | head -5

# Markdown
sif search search "chromosome" --md | head -15
```

**Check:** JSON valid, CSV has headers, Markdown readable

---

## Test 11: ls File Tree

```bash
sif ls scholar-test
```

**Check:** Shows 1/2/3/4 subdirectory structure with paper files

---

## Test 12: Multi-get Batch Retrieval

```bash
# Glob pattern with byte limit
sif get multi-get "*.md" -b 500
```

**Check:** Returns multiple documents (truncated to 500 bytes each)

---

## Test 13: Search with Filters

```bash
# Limit results
sif search search "DNA" -n 3

# Minimum score filter
sif search search "DNA" --min-score 0.3

# Explain mode
sif search search "DNA" --explain
```

**Check:** `-n 3` returns exactly 3, `--min-score` filters low scores, `--explain` shows score breakdown

---

## Test 14: Context Enhancement

```bash
# Add collection-level context
sif context add collection scholar-test "学术论文集合，包含生物医学研究论文，按 PMID 编号组织"

# Add path-level context
sif context add path /Users/forrest/SynologyDrive/Obsidian/ScholarCopilot-Dev/raw/markdown/3 "Group 3 论文"

# Verify
sif context list

# Check context in search results
sif search search "chromosome" --full
```

**Check:** Search results include context_description field

---

## Test 15: Full Content Search

```bash
sif search search "Saccharomyces cerevisiae" --full -n 1
```

**Check:** Returns full paper content (or large excerpt)

---

## Test 16: Cleanup

```bash
# Remove test collection
echo "y" | sif collection remove scholar-test

# Confirm removed
sif collection list

# Clean up
unset SIF_DB_PATH
rm -f /tmp/sif-scholar-test.sqlite
```

---

## Key Focus Areas

- Indexing speed and memory usage for 307 papers
- Short filename lookup works with PMID numbers (pure digits)
- Embedding generation speed (first run downloads ~1.2GB model)
- Vector search returns semantically relevant results (not just keyword match)
- Hybrid search (BM25 + Vector + RRF) produces better ranking than either alone
- Search performance and result truncation for long documents
