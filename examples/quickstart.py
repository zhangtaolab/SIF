#!/usr/bin/env python3
"""SIF quickstart: index a temporary notes directory and search it.

Run from a checkout with the development environment installed:

    python examples/quickstart.py

The example uses a temporary ``SIF_DB_PATH``, so it never touches your real
index. It drives the same CLI surface a user would — ``collection add``,
``index update``, BM25 ``search``, and ``status`` — then shows the equivalent
Python API.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLI = [sys.executable, "-m", "sif.cli.main"]


def run_cli(args: list[str], env: dict[str, str]) -> str:
    """Run one ``sif`` command and return its stdout; raise on failure."""
    result = subprocess.run(
        [*CLI, *args],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"`sif {' '.join(args)}` failed (exit {result.returncode}): {detail}")
    return result.stdout


def main() -> int:
    """Run the CLI walkthrough against a throwaway database."""
    with tempfile.TemporaryDirectory(prefix="sif-quickstart-") as raw_tmp:
        tmp = Path(raw_tmp)
        docs = tmp / "notes"
        docs.mkdir()
        (docs / "python.md").write_text(
            "# Python\n\nPython is a readable programming language.\n", encoding="utf-8"
        )
        (docs / "search.md").write_text(
            "# Search\n\nHybrid search combines BM25 keywords with vectors.\n",
            encoding="utf-8",
        )

        env = os.environ.copy()
        env["SIF_DB_PATH"] = str(tmp / "sif.db")
        env["PYTHONPATH"] = os.pathsep.join(
            [str(PROJECT_ROOT / "src"), env.get("PYTHONPATH", "")]
        ).rstrip(os.pathsep)

        print(f"Using temporary database: {env['SIF_DB_PATH']}")
        print(f"Indexing: {docs}")
        print(run_cli(["collection", "add", str(docs), "--name", "quickstart"], env), end="")
        print(run_cli(["index", "update"], env), end="")

        payload = json.loads(run_cli(["search", "search", "Python", "--json"], env))
        print(f"\nBM25 results for 'Python': {len(payload)}")
        for rank, result in enumerate(payload, start=1):
            label = result.get("title") or result.get("path") or "?"
            print(f"  {rank}. {label}")

        print(run_cli(["status"], env), end="")

    print("\nPython API equivalent:")
    print("  from sif.config.settings import get_settings")
    print("  from sif.database.database import Database")
    print("  from sif.search.bm25 import BM25Searcher")
    print("  settings = get_settings()")
    print("  with Database(str(settings.get_db_path())) as db:")
    print("      results = BM25Searcher(db.connection).search('Python')")
    return 0


if __name__ == "__main__":
    sys.exit(main())
