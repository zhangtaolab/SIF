#!/usr/bin/env python3
"""Generate the deterministic bench fixture pack (synthetic corpus + graded queries).

Output is a pure function of ``--seed`` (default 16): reruns are
byte-identical, which ``--check`` enforces as a drift gate against the
committed pack. The corpus is SYNTHETIC, built only from the seeded word
lists in this script — it must never contain real personal-KB content
(Phase 16 D-01). Relevance is keyed by corpus-relative POSIX paths
(D-02), and every query carries a fixed tuning|heldout split (D-03).
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

CATEGORIES = ("keyword", "synonym", "multilingual", "rival")
QUERIES_PER_CATEGORY = 14
HELDOUT_PER_CATEGORY = 5  # 5 held-out x 4 categories = 20; the other 9 x 4 = 36 tuning
KEYWORD_DOC_COUNT = 40
SYNONYM_TOPIC_COUNT = 19  # 2 docs per topic -> 38 docs
MULTILINGUAL_TOPIC_COUNT = 18  # primary + companion per topic -> 36 docs
RIVAL_TOPIC_COUNT = 18  # authoritative + draft per pair -> 36 docs

# Distinctive two-syllable codenames for the keyword category: doc i uses
# syllables 2i/2i+1 joined, so every document owns a unique exact term.
SYLLABLES = (
    "zor",
    "vex",
    "qua",
    "myr",
    "tal",
    "ven",
    "kel",
    "pri",
    "dun",
    "sha",
    "obe",
    "lir",
    "cas",
    "tel",
    "nov",
    "bra",
    "ful",
    "gri",
    "hed",
    "jol",
    "nam",
    "pex",
    "rhu",
    "syl",
    "tho",
    "ulp",
    "wok",
    "xan",
    "yev",
    "zet",
    "amb",
    "bri",
    "col",
    "dra",
    "eps",
    "fro",
    "gan",
    "hil",
    "irk",
    "jyn",
    "kor",
    "lun",
    "mop",
    "nir",
    "ost",
    "pan",
    "qel",
    "ron",
    "sal",
    "tiv",
    "urk",
    "vos",
    "wol",
    "xer",
    "yan",
    "zun",
    "ard",
    "eld",
    "ilm",
    "usk",
    "bat",
    "wex",
    "yol",
    "zap",
    "bel",
    "cim",
    "dol",
    "efl",
    "gol",
    "hup",
    "ivy",
    "jor",
    "kex",
    "lav",
    "mot",
    "nul",
    "orp",
    "pil",
    "quv",
    "ras",
)

FILLER_ADJECTIVES = (
    "steady",
    "compact",
    "rugged",
    "precise",
    "modular",
    "silent",
    "robust",
    "nimble",
    "dense",
    "clear",
    "portable",
    "resilient",
    "tidy",
    "swift",
    "ample",
    "level",
    "polished",
    "measured",
    "orderly",
    "compact",
    "guarded",
    "seasonal",
    "typical",
    "varied",
)
FILLER_NOUNS = (
    "console",
    "ledger",
    "bench",
    "harness",
    "registry",
    "manifest",
    "roster",
    "cache",
    "archive",
    "notebook",
    "workbench",
    "portfolio",
    "checklist",
    "digest",
    "index",
    "summary",
    "catalog",
    "digest",
    "journal",
    "digest",
    "folio",
    "compendium",
    "record",
    "survey",
)
FILLER_VERBS = (
    "records",
    "inspects",
    "balances",
    "archives",
    "routes",
    "profiles",
    "summarizes",
    "validates",
    "schedules",
    "reconciles",
    "annotates",
    "correlates",
    "revises",
    "surveys",
    "timestamps",
    "cross-checks",
    "normalizes",
    "dispatches",
    "samples",
    "reconciles",
)

# Synonym topics: (headword, doc vocabulary, query paraphrase synonyms).
# Docs carry the headword + canonical vocabulary; queries paraphrase with the
# synonyms, so the category leans on the vector leg, not exact term overlap.
SYNONYM_TOPICS = (
    ("navigation", ("wayfinding", "compass", "bearing"), ("route", "planning")),
    ("fermentation", ("brewing", "yeast", "mash"), ("culture", "starter")),
    ("holography", ("interference", "fringes", "emulsion"), ("light", "recording")),
    ("cartography", ("surveying", "contours", "projections"), ("mapmaking", "terrain")),
    ("acoustics", ("resonance", "harmonics", "damping"), ("sound", "vibration")),
    ("metallurgy", ("smelting", "alloys", "tempering"), ("metal", "refining")),
    ("botany", ("specimens", "taxonomy", "foliage"), ("plants", "classification")),
    ("astronomy", ("ephemeris", "parallax", "apertures"), ("stars", "observation")),
    ("cryptography", ("ciphers", "keys", "entropy"), ("encryption", "secrecy")),
    ("hydrology", ("runoff", "aquifers", "salinity"), ("water", "drainage")),
    ("linguistics", ("morphology", "syntax", "phonemes"), ("grammar", "language")),
    ("thermodynamics", ("enthalpy", "isotherms", "cycles"), ("heat", "energy")),
    ("origami", ("folding", "creases", "modules"), ("paper", "figures")),
    ("seismology", ("faults", "tremors", "epicenters"), ("earthquake", "waves")),
    ("photography", ("exposure", "focal", "film"), ("imaging", "pictures")),
    ("beekeeping", ("hives", "combs", "swarms"), ("apiary", "honey")),
    ("glaciology", ("moraines", "crevasses", "firn"), ("ice", "glaciers")),
    ("typography", ("kerning", "serifs", "leading"), ("fonts", "text")),
    ("mycology", ("spores", "mycelium", "fruiting"), ("fungi", "mushrooms")),
)

# Multilingual topics: (english phrase, exact contiguous Chinese run). The
# Chinese run appears in docs surrounded by non-CJK characters, so the FTS
# porter tokenizer keeps it as one token and queries match it exactly
# (research Pitfall 3: never rely on mid-run prefixes).
MULTILINGUAL_TOPICS = (
    ("machine learning", "机器学习"),
    ("deep learning", "深度学习"),
    ("neural networks", "神经网络"),
    ("natural language processing", "自然语言处理"),
    ("data mining", "数据挖掘"),
    ("knowledge graphs", "知识图谱"),
    ("cloud computing", "云计算"),
    ("distributed systems", "分布式系统"),
    ("database indexing", "数据库索引"),
    ("cache strategy", "缓存策略"),
    ("message queues", "消息队列"),
    ("microservice architecture", "微服务架构"),
    ("container orchestration", "容器编排"),
    ("version control", "版本控制"),
    ("continuous integration", "持续集成"),
    ("monitoring alerts", "监控告警"),
    ("load balancing", "负载均衡"),
    ("data visualization", "数据可视化"),
)

# Rival topics: near-duplicate pairs — an authoritative field guide and an
# abbreviated draft sharing the topic terms; graded ordering distinguishes them.
RIVAL_TOPICS = (
    ("flux capacitor", "charge regulation"),
    ("warp coil", "plasma containment"),
    ("phase array", "signal alignment"),
    ("ion thruster", "fuel efficiency"),
    ("quantum lattice", "error correction"),
    ("photon sieve", "light concentration"),
    ("gravity well", "trajectory assist"),
    ("muon detector", "particle counting"),
    ("tachyon beacon", "temporal sync"),
    ("plasma conduit", "heat shielding"),
    ("neutrino sink", "lepton capture"),
    ("boson trap", "field containment"),
    ("axion mirror", "dark matter"),
    ("gluon tether", "color confinement"),
    ("lepton sail", "charge steering"),
    ("quark forge", "element synthesis"),
    ("hadron lens", "beam focusing"),
    ("fermion gate", "spin filtering"),
)


def _filler_sentence(rng: random.Random) -> str:
    """One seeded filler sentence from the shared vocabulary pools."""
    adjective = rng.choice(FILLER_ADJECTIVES)
    noun = rng.choice(FILLER_NOUNS)
    verb = rng.choice(FILLER_VERBS)
    return f"A {adjective} {noun} {verb} the daily entries without manual review."


def _codename(index: int) -> str:
    """Distinctive exact term for keyword doc ``index``."""
    return SYLLABLES[2 * index] + SYLLABLES[2 * index + 1]


def _keyword_docs(rng: random.Random) -> dict[str, str]:
    """Keyword corpus: each doc owns a unique codename and mentions its successor."""
    files: dict[str, str] = {}
    for i in range(KEYWORD_DOC_COUNT):
        codename = _codename(i)
        sentences = [
            f"The {codename} protocol governs telemetry alignment for station {i}"
            " in the northern array.",
            _filler_sentence(rng),
            f"Operators archive {codename} logs weekly to keep the bench current.",
        ]
        if i + 1 < KEYWORD_DOC_COUNT:
            sentences.append(
                f"The successor module {_codename(i + 1)} extends this protocol"
                " with wider handshakes.",
            )
        files[f"corpus/keyword/kw-{i:03d}.md"] = (
            f"# {codename.capitalize()} Protocol Notes\n\n" + " ".join(sentences) + "\n"
        )
    return files


def _synonym_docs(rng: random.Random) -> dict[str, str]:
    """Synonym corpus: a handbook (canonical vocabulary) + field guide per topic."""
    files: dict[str, str] = {}
    for k, (head, vocab, _synonyms) in enumerate(SYNONYM_TOPICS):
        v1, v2, v3 = vocab
        handbook = (
            f"# {head.capitalize()} Handbook\n\n"
            f"This {head} handbook covers {v1}, {v2}, and {v3} across graded"
            f" chapters. {_filler_sentence(rng)} Each {head} chapter pairs"
            f" the {rng.choice(FILLER_NOUNS)} with field notes and worked"
            " examples for independent study.\n"
        )
        guide = (
            f"# {head.capitalize()} Field Guide\n\n"
            f"A compact {head} reference for {v1} and {v2}."
            f" {_filler_sentence(rng)} Margins list the {head} essentials"
            " for quick revision on site.\n"
        )
        files[f"corpus/synonym/syn-{2 * k:03d}.md"] = handbook
        files[f"corpus/synonym/syn-{2 * k + 1:03d}.md"] = guide
    return files


def _multilingual_docs(rng: random.Random) -> dict[str, str]:
    """Multilingual corpus: English prose with exact contiguous Chinese runs."""
    files: dict[str, str] = {}
    for k, (english, chinese) in enumerate(MULTILINGUAL_TOPICS):
        title_english = english.title()
        primary = (
            f"# {title_english} Notes {chinese}\n\n"
            f"This survey covers {chinese} alongside {english} fundamentals for"
            f" team {k}. {_filler_sentence(rng)} Practical {english} examples"
            f" follow the {chinese} primer, and closing chapters revisit"
            f" {chinese} with review questions.\n"
        )
        companion = (
            f"# {title_english} Companion\n\n"
            f"A companion brief connecting {chinese} with {english} workflows in"
            f" practice. {_filler_sentence(rng)} Teams paste the {chinese}"
            " checklist into their onboarding pages.\n"
        )
        files[f"corpus/multilingual/ml-{k:03d}.md"] = primary
        files[f"corpus/multilingual/ml-{k + MULTILINGUAL_TOPIC_COUNT:03d}.md"] = companion
    return files


def _rival_docs(rng: random.Random) -> dict[str, str]:
    """Rival corpus: authoritative field guides vs abbreviated near-duplicate drafts."""
    files: dict[str, str] = {}
    for p, (topic, focus) in enumerate(RIVAL_TOPICS):
        guide = (
            f"# {topic.title()} Field Guide\n\n"
            f"The authoritative {topic} guide covers {focus} in full detail across"
            f" every operating mode. {_filler_sentence(rng)} Chapters walk through"
            f" {topic} assembly, then {focus}, then the complete {topic}"
            f" commissioning sequence. Appendix B compares {topic} variants under"
            " sustained load with recorded measurements.\n"
        )
        draft = (
            f"# {topic.title()} Draft Notes\n\n"
            f"An abbreviated draft summarizing the {topic} guide: {focus} in one"
            f" page. {_filler_sentence(rng)} The full {topic} treatment lives in"
            " the field guide.\n"
        )
        files[f"corpus/rival/riv-{p:03d}-a.md"] = guide
        files[f"corpus/rival/riv-{p:03d}-b.md"] = draft
    return files


def _split_for(index: int) -> str:
    """Fixed split assignment: first queries tune, the last 5 per category hold out."""
    return "heldout" if index >= QUERIES_PER_CATEGORY - HELDOUT_PER_CATEGORY else "tuning"


def _build_queries() -> list[dict]:
    """56 graded queries: 14 per category, 9 tuning + 5 held-out each."""
    queries: list[dict] = []

    # Keyword docs queried by their exact codename; the predecessor doc (which
    # mentions the codename once in its successor line) is the grade-2 result.
    # Relevance keys are corpus-relative (under the declared corpus_root
    # "corpus"), never pack-relative (D-02).
    keyword_targets = (3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 1, 5, 9, 13)
    for j, target in enumerate(keyword_targets):
        queries.append(
            {
                "query": f"{_codename(target)} protocol",
                "category": "keyword",
                "split": _split_for(j),
                "relevance": {
                    f"keyword/kw-{target:03d}.md": 3,
                    f"keyword/kw-{target - 1:03d}.md": 2,
                },
            }
        )

    # Synonym queries paraphrase the topic vocabulary, sharing only the headword.
    for k, (head, _vocab, synonyms) in enumerate(SYNONYM_TOPICS[:QUERIES_PER_CATEGORY]):
        queries.append(
            {
                "query": f"{head} {' '.join(synonyms)}",
                "category": "synonym",
                "split": _split_for(k),
                "relevance": {
                    f"synonym/syn-{2 * k:03d}.md": 3,
                    f"synonym/syn-{2 * k + 1:03d}.md": 2,
                },
            }
        )

    # Multilingual queries pair the English phrase with the exact Chinese run;
    # the companion doc (same run, fewer mentions) is the grade-2 result.
    for k, (english, chinese) in enumerate(MULTILINGUAL_TOPICS[:QUERIES_PER_CATEGORY]):
        queries.append(
            {
                "query": f"{english} {chinese}",
                "category": "multilingual",
                "split": _split_for(k),
                "relevance": {
                    f"multilingual/ml-{k:03d}.md": 3,
                    f"multilingual/ml-{k + MULTILINGUAL_TOPIC_COUNT:03d}.md": 2,
                },
            }
        )

    # Rival queries hit the near-duplicate pair; the next pair's guide is the
    # graded non-relevant (0) neighbor.
    for p in range(QUERIES_PER_CATEGORY):
        topic, focus = RIVAL_TOPICS[p]
        neighbor = (p + 1) % RIVAL_TOPIC_COUNT
        queries.append(
            {
                "query": f"{topic} {focus.split()[0]}",
                "category": "rival",
                "split": _split_for(p),
                "relevance": {
                    f"rival/riv-{p:03d}-a.md": 3,
                    f"rival/riv-{p:03d}-b.md": 2,
                    f"rival/riv-{neighbor:03d}-a.md": 0,
                },
            }
        )
    return queries


def build_pack(seed: int) -> dict[str, str]:
    """Build the full pack as {relative POSIX path: file content} — deterministic."""
    rng = random.Random(seed)
    files: dict[str, str] = {}
    files.update(_keyword_docs(rng))
    files.update(_synonym_docs(rng))
    files.update(_multilingual_docs(rng))
    files.update(_rival_docs(rng))
    pack = {
        "version": 1,
        "corpus_root": "corpus",
        "relevance_key": "path",
        "queries": _build_queries(),
    }
    files["queries.json"] = json.dumps(pack, indent=2, sort_keys=True) + "\n"
    return files


def write_pack(out: Path, files: dict[str, str]) -> None:
    """Write every generated file under ``out`` (sorted for stable output order)."""
    for rel in sorted(files):
        target = out / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(files[rel], encoding="utf-8")


# Pack-root files committed alongside the generated pack (held-out evidence
# snapshot and the hand-authored README). The generator does not produce
# them, but the drift gate must accept them (WR-03).
ALLOWED_EXTRA_FILES = {"heldout_defaults.json", "README.md"}


def check_pack(out: Path, files: dict[str, str]) -> list[str]:
    """Diff the committed pack against generator output; return drifting paths.

    Drift is bidirectional (WR-03): missing or drifted expected files AND
    unexpected committed files anywhere under the pack root. A stray file
    under ``corpus/`` silently changes every measured metric while a missing
    one only fails loudly, so the gate must catch both — the
    intentionally-committed evidence/README files are allowlisted instead.
    """
    drift: list[str] = []
    for rel in sorted(files):
        target = out / rel
        if not target.is_file():
            drift.append(f"missing: {rel}")
        elif target.read_text(encoding="utf-8") != files[rel]:
            drift.append(f"drifted: {rel}")
    expected = set(files) | ALLOWED_EXTRA_FILES
    for path in sorted(out.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(out).as_posix()
        if rel not in expected:
            drift.append(f"unexpected: {rel}")
    return drift


def main() -> int:
    """Generate (or drift-check) the bench fixture pack."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=16, help="generation seed")
    parser.add_argument(
        "--out",
        type=Path,
        default=PROJECT_ROOT / "tests" / "fixtures" / "bench",
        help="pack output directory",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the committed pack matches generator output; exit 1 on drift",
    )
    args = parser.parse_args()

    files = build_pack(args.seed)
    if args.check:
        drift = check_pack(args.out, files)
        if drift:
            for line in drift:
                sys.stderr.write(f"{line}\n")
            sys.stderr.write(
                f"FAIL: {len(drift)} path(s) drifted from the generator output;"
                " rerun scripts/generate_bench_fixture.py and commit the result\n"
            )
            return 1
        print(f"OK: {args.out} matches generator output ({len(files)} files)")  # noqa: T201
        return 0

    write_pack(args.out, files)
    sys.stderr.write(f"Generated {len(files)} files under {args.out}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
