# Bench Fixture Pack

Committed synthetic benchmark corpus + graded queries for `sif bench`
(Phase 16, EVAL-02). This pack is the measuring instrument for the fusion
sweep and the held-out defaults evidence.

## This corpus is synthetic — never commit a real KB

Every document here is generated from seeded word lists in
`scripts/generate_bench_fixture.py` (D-01). It must NEVER contain real
personal-knowledge-base content: no personal notes, paths, names, or
private material. Running the generator over a real corpus is not a
supported workflow; a real-KB benchmark is an optional local run only.

## Layout

```
tests/fixtures/bench/
├── corpus/
│   ├── keyword/*.md        # 40 docs, each owning a unique exact codename
│   ├── synonym/*.md        # 38 docs: handbook + field guide per topic
│   ├── multilingual/*.md   # 36 docs mixing English and exact Chinese runs
│   └── rival/*.md          # 36 docs: authoritative guide vs abbreviated draft pairs
├── queries.json            # 56 graded queries (36 tuning / 20 held-out)
└── README.md
```

## Queries and grading

`queries.json` declares `corpus_root: "corpus"` and
`relevance_key: "path"` — relevance keys are POSIX paths relative to the
corpus root (never document ids, which are random UUIDs at index time).
Each query carries:

- `query`: the query text
- `category`: `keyword` (exact distinctive terms), `synonym`
  (paraphrase pressure on the vector leg), `multilingual` (English +
  Chinese; Chinese terms are exact contiguous runs present in the
  documents, respecting the FTS porter tokenizer), or `rival`
  (near-duplicate pairs distinguished by graded ordering)
- `split`: `tuning` or `heldout` — 9 tuning + 5 held-out per category
- `relevance`: at most 5 entries mapping corpus-relative paths to grades

Grades follow the D-02 scale: `0` irrelevant, `1` partial, `2` relevant,
`3` highly relevant. Every query carries at least one `3` and one `2`;
rival queries additionally name a graded `0` neighbor.

## Tuning / held-out contract

The sweep (16-04) may consult **tuning** queries only. Shipped-default
changes require held-out evidence at delta >= 0.01 mean nDCG@10 (EVAL-04).
The split is fixed in the fixture; there is no runtime-random splitting.

## Regenerating and the drift gate

```bash
python scripts/generate_bench_fixture.py           # regenerate (seed 16)
python scripts/generate_bench_fixture.py --check   # drift gate: exit 1 on any diff
```

Output is a pure function of the seed: reruns are byte-identical, and
`--check` fails if a committed file drifts from the generator output.
To change the pack, edit the generator and commit the regenerated files
in the same change.
