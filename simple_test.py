#!/usr/bin/env python3
"""
DocSift 简单验证脚本
测试不依赖外部库的模块
"""

import sys
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_cli_only():
    """只测试CLI（不依赖外部库）"""
    print("Testing CLI...")
    try:
        from click.testing import CliRunner
        from docsift.cli.main import cli
        
        runner = CliRunner()
        
        # 测试 --help
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "DocSift" in result.output
        
        print("✅ CLI tests passed")
        print("\nAvailable commands:")
        # 提取命令列表
        for line in result.output.split('\n'):
            if line.strip().startswith('collection') or line.strip().startswith('search'):
                print(f"  {line.strip()}")
        
        return True
    except Exception as e:
        print(f"❌ CLI test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_project_structure():
    """测试项目结构完整性"""
    print("\nTesting project structure...")
    
    required_files = [
        "pyproject.toml",
        "README.md",
        "Makefile",
        ".pre-commit-config.yaml",
        ".github/workflows/ci.yml",
        "src/docsift/__init__.py",
        "src/docsift/cli/main.py",
        "src/docsift/database/__init__.py",
        "src/docsift/search/__init__.py",
        "src/docsift/indexing/__init__.py",
        "src/docsift/mcp/__init__.py",
        "tests/conftest.py",
    ]
    
    base_path = Path(__file__).parent
    missing = []
    
    for file_path in required_files:
        full_path = base_path / file_path
        if not full_path.exists():
            missing.append(file_path)
    
    if missing:
        print(f"❌ Missing files: {missing}")
        return False
    else:
        print(f"✅ All {len(required_files)} required files present")
        return True

def test_pyproject():
    """测试 pyproject.toml"""
    print("\nTesting pyproject.toml...")
    
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib
    
    pyproject_path = Path(__file__).parent / "pyproject.toml"
    
    with open(pyproject_path, "rb") as f:
        config = tomllib.load(f)
    
    # 检查必要字段
    assert "project" in config
    assert config["project"]["name"] == "docsift"
    assert "dependencies" in config["project"]
    
    # 检查 CLI 入口点
    assert "scripts" in config["project"]
    assert "docsift" in config["project"]["scripts"]
    
    print("✅ pyproject.toml is valid")
    print(f"  Project: {config['project']['name']}")
    print(f"  Version: {config['project']['version']}")
    print(f"  Dependencies: {len(config['project']['dependencies'])}")
    
    return True

def count_files():
    """统计项目文件"""
    print("\nProject statistics:")
    
    base_path = Path(__file__).parent
    
    # Python 文件
    py_files = list(base_path.rglob("*.py"))
    print(f"  Python files: {len(py_files)}")
    
    # 测试文件
    test_files = list((base_path / "tests").rglob("test_*.py"))
    print(f"  Test files: {len(test_files)}")
    
    # 文档文件
    md_files = list((base_path / "docs").rglob("*.md"))
    print(f"  Documentation files: {len(md_files)}")
    
    return True

def main():
    """运行所有测试"""
    print("=" * 60)
    print("DocSift Simple Verification")
    print("=" * 60)
    
    tests = [
        ("Project Structure", test_project_structure),
        ("pyproject.toml", test_pyproject),
        ("CLI", test_cli_only),
        ("Statistics", count_files),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"❌ {name} test crashed: {e}")
            import traceback
            traceback.print_exc()
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
        print("\n🎉 Project structure is valid!")
        print("\nTo install dependencies, run:")
        print("  pip install -e '.[all]'")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
