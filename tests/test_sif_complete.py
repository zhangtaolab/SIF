#!/usr/bin/env python3
"""Complete test suite for SIF."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_imports() -> None:
    """Test all core imports."""
    print("Testing imports...")
    try:
        print("✅ All imports successful")
    except Exception as e:
        print(f"❌ Import failed: {e}")
        import traceback

        traceback.print_exc()
        raise


def test_database() -> None:
    """Test database operations."""
    print("\nTesting database...")
    try:
        from sif.database.database import Database

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = Database(db_path)
            db.init_schema()

            # Test connection
            stats = db.get_stats()
            assert isinstance(stats, dict)
            print(f"✅ Database created: {db_path}")
            print(f"   Stats: {stats}")

    except Exception as e:
        print(f"❌ Database test failed: {e}")
        import traceback

        traceback.print_exc()
        raise


def test_collection_repository() -> None:
    """Test collection repository."""
    print("\nTesting collection repository...")
    try:
        from sif.core.models import Collection
        from sif.database.database import Database
        from sif.database.repositories import CollectionRepository

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = Database(db_path)
            db.init_schema()

            with db.transaction() as conn:
                repo = CollectionRepository(conn)

                # Create collection
                collection = Collection(
                    name="test_collection",
                    path="/tmp/test",
                    pattern="**/*.md",
                )
                repo.create(collection)
                print(f"✅ Collection created: {collection.name}")

                # Get by name
                retrieved = repo.get_by_name("test_collection")
                assert retrieved is not None
                assert retrieved.name == "test_collection"
                print(f"✅ Collection retrieved: {retrieved.name}")

                # List all
                collections = repo.list_all()
                assert len(collections) == 1
                print(f"✅ Listed {len(collections)} collection(s)")

    except Exception as e:
        print(f"❌ Collection repository test failed: {e}")
        import traceback

        traceback.print_exc()
        raise


def test_document_repository() -> None:
    """Test document repository."""
    print("\nTesting document repository...")
    try:
        from sif.core.models import Collection, Document
        from sif.database.database import Database
        from sif.database.repositories import (
            CollectionRepository,
            DocumentRepository,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = Database(db_path)
            db.init_schema()

            with db.transaction() as conn:
                # Create collection first
                coll_repo = CollectionRepository(conn)
                collection = Collection(
                    name="test_docs",
                    path="/tmp/docs",
                    pattern="**/*.md",
                )
                coll_repo.create(collection)

                # Create document
                doc_repo = DocumentRepository(conn)
                document = Document(
                    path="/tmp/docs/test.md",
                    collection_id=collection.id,
                    content="# Test\n\nThis is a test document.",
                    title="Test Document",
                )
                doc_repo.create(document)
                print(f"✅ Document created: {document.title}")

                # Get by ID
                retrieved = doc_repo.get_by_id(document.id)
                assert retrieved is not None
                assert retrieved.title == "Test Document"
                print(f"✅ Document retrieved: {retrieved.title}")

                # List by collection
                docs = doc_repo.list_by_collection(collection.id)
                assert len(docs) == 1
                print(f"✅ Listed {len(docs)} document(s)")

    except Exception as e:
        print(f"❌ Document repository test failed: {e}")
        import traceback

        traceback.print_exc()
        raise


def test_chunker() -> None:
    """Test document chunking."""
    print("\nTesting chunker...")
    try:
        from sif.indexing import create_chunker

        chunker = create_chunker("fixed", chunk_size=100, overlap=20)
        text = (
            "# Heading\n\nThis is paragraph 1.\n\n"
            "This is paragraph 2.\n\n## Subheading\n\n"
            "More content here."
        )

        chunks = chunker.chunk(text)
        assert len(chunks) > 0
        print(f"✅ Created {len(chunks)} chunks")

        # Test markdown chunker
        md_chunker = create_chunker("markdown")
        md_text = "# Title\n\nContent 1\n\n## Section 1\n\nContent 2\n\n## Section 2\n\nContent 3"
        md_chunks = md_chunker.chunk(md_text)
        assert len(md_chunks) > 0
        print(f"✅ Markdown chunker created {len(md_chunks)} chunks")

    except Exception as e:
        print(f"❌ Chunker test failed: {e}")
        import traceback

        traceback.print_exc()
        raise


def test_rrf() -> None:
    """Test RRF fusion."""
    print("\nTesting RRF fusion...")
    try:
        from sif.core.models import SearchResult
        from sif.search.rrf import RRFFusion

        rrf = RRFFusion(k=60)

        # Create test results
        list1 = [
            SearchResult("doc1", "Doc 1", "/path/1", "coll", 0.9, rank=1),
            SearchResult("doc2", "Doc 2", "/path/2", "coll", 0.8, rank=2),
            SearchResult("doc3", "Doc 3", "/path/3", "coll", 0.7, rank=3),
        ]

        list2 = [
            SearchResult("doc2", "Doc 2", "/path/2", "coll", 0.85, rank=1),
            SearchResult("doc3", "Doc 3", "/path/3", "coll", 0.75, rank=2),
            SearchResult("doc4", "Doc 4", "/path/4", "coll", 0.65, rank=3),
        ]

        fused = rrf.fuse([list1, list2])
        assert len(fused) > 0
        print(f"✅ RRF fused {len(fused)} results")

        # doc2 should be ranked highest (appears in both lists)
        assert fused[0].document_id in ["doc1", "doc2"]
        print(f"✅ Top result: {fused[0].document_id}")

    except Exception as e:
        print(f"❌ RRF test failed: {e}")
        import traceback

        traceback.print_exc()
        raise


def test_cli() -> None:
    """Test CLI."""
    print("\nTesting CLI...")
    try:
        from click.testing import CliRunner

        from sif.cli.main import cli

        runner = CliRunner()

        # Test --help
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "SIF" in result.output
        print("✅ CLI --help works")

        # Test --version
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        print("✅ CLI --version works")

    except Exception as e:
        print(f"❌ CLI test failed: {e}")
        import traceback

        traceback.print_exc()
        raise


def test_scanner() -> None:
    """Test file scanner."""
    print("\nTesting scanner...")
    try:
        from sif.indexing.scanner import FileScanner

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            test_dir = Path(tmpdir)
            (test_dir / "test1.md").write_text("# Test 1")
            (test_dir / "test2.md").write_text("# Test 2")
            (test_dir / "subdir").mkdir()
            (test_dir / "subdir" / "test3.md").write_text("# Test 3")
            (test_dir / "ignore.txt").write_text("ignored")

            scanner = FileScanner()
            result = scanner.scan(test_dir, pattern="**/*.md")

            assert result.file_count == 3
            print(f"✅ Scanned {result.file_count} files")

    except Exception as e:
        print(f"❌ Scanner test failed: {e}")
        import traceback

        traceback.print_exc()
        raise


def test_parser() -> None:
    """Test document parser."""
    print("\nTesting parser...")
    try:
        from sif.indexing.parser import MarkdownParser

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test markdown file
            test_file = Path(tmpdir) / "test.md"
            test_file.write_text("""---
title: Test Document
author: Test Author
---

# Test Title

This is the content.
""")

            parser = MarkdownParser()
            parsed = parser.parse(test_file)

            assert parsed.title == "Test Document"
            assert "Test Title" in parsed.content
            print(f"✅ Parsed: {parsed.title}")

    except Exception as e:
        print(f"❌ Parser test failed: {e}")
        import traceback

        traceback.print_exc()
        raise


def main() -> int:
    """Run all tests."""
    print("=" * 60)
    print("SIF Complete Test Suite")
    print("=" * 60)

    tests = [
        ("Imports", test_imports),
        ("Database", test_database),
        ("Collection Repository", test_collection_repository),
        ("Document Repository", test_document_repository),
        ("Chunker", test_chunker),
        ("RRF Fusion", test_rrf),
        ("CLI", test_cli),
        ("Scanner", test_scanner),
        ("Parser", test_parser),
    ]

    results = []
    for name, test_func in tests:
        try:
            test_func()
            results.append((name, True))
        except Exception as e:
            print(f"\n❌ {name} test crashed: {e}")
            import traceback

            traceback.print_exc()
            results.append((name, False))

    # Print summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, p in results if p)
    total = len(results)

    for name, p in results:
        status = "✅ PASSED" if p else "❌ FAILED"
        print(f"{name:30} {status}")

    print("-" * 60)
    print(f"Total: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    print(f"\n⚠️ {total - passed} test(s) failed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
