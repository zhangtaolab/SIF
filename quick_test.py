#!/usr/bin/env python3
"""
DocSift 快速验证脚本
运行基本功能测试，确保核心模块正常工作
"""

import sys
import tempfile
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """测试所有核心导入"""
    print("Testing imports...")
    try:
        from docsift.database import DatabaseConnection
        from docsift.search import HybridSearchStrategy, RRFFusion
        from docsift.indexing import DocumentIndexer
        from docsift.embedding import EmbeddingManager
        from docsift.cli.main import cli
        from docsift.mcp.server import MCPServer
        print("✅ All imports successful")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database():
    """测试数据库功能"""
    print("\nTesting database...")
    try:
        from docsift.database import DatabaseConnection, CollectionRepository
        
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            conn = DatabaseConnection(str(db_path))
            
            # 测试连接
            with conn.connect() as db:
                cursor = db.execute("SELECT 1")
                assert cursor.fetchone()[0] == 1
            
            print("✅ Database tests passed")
            return True
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_chunker():
    """测试文档分块"""
    print("\nTesting chunker...")
    try:
        from docsift.indexing.chunker import create_chunker
        
        chunker = create_chunker("fixed", chunk_size=100, overlap=20)
        text = "# Heading\n\nThis is paragraph 1.\n\nThis is paragraph 2.\n\n## Subheading\n\nMore content here."
        
        chunks = chunker.chunk(text)
        assert len(chunks) > 0
        assert all(hasattr(c, 'content') for c in chunks)
        
        print(f"✅ Chunker tests passed ({len(chunks)} chunks)")
        return True
    except Exception as e:
        print(f"❌ Chunker test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_search():
    """测试搜索功能"""
    print("\nTesting search...")
    try:
        from docsift.search.rrf import RRFFusion
        
        # 测试 RRF 融合
        rrf = RRFFusion(k=60)
        
        list1 = [("doc1", 0.9), ("doc2", 0.8), ("doc3", 0.7)]
        list2 = [("doc2", 0.85), ("doc3", 0.75), ("doc4", 0.65)]
        
        result = rrf.fuse([list1, list2])
        assert len(result) > 0
        assert result[0][0] in ["doc1", "doc2"]  # doc1 或 doc2 应该排第一
        
        print("✅ Search tests passed")
        return True
    except Exception as e:
        print(f"❌ Search test failed: {e}")
        return False

def test_cli():
    """测试 CLI"""
    print("\nTesting CLI...")
    try:
        from click.testing import CliRunner
        from docsift.cli.main import cli
        
        runner = CliRunner()
        
        # 测试 --version
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        
        # 测试 --help
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "DocSift" in result.output
        
        print("✅ CLI tests passed")
        return True
    except Exception as e:
        print(f"❌ CLI test failed: {e}")
        return False

def main():
    """运行所有测试"""
    print("=" * 60)
    print("DocSift Quick Verification")
    print("=" * 60)
    
    tests = [
        ("Imports", test_imports),
        ("Database", test_database),
        ("Chunker", test_chunker),
        ("Search", test_search),
        ("CLI", test_cli),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"❌ {name} test crashed: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, p in results if p)
    total = len(results)
    
    for name, p in results:
        status = "✅ PASSED" if p else "❌ FAILED"
        print(f"{name:20} {status}")
    
    print("-" * 60)
    print(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! DocSift is ready to use.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
