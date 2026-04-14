#!/usr/bin/env python3
"""
DocSift Import Verification Script

This script verifies that all key modules and classes can be imported successfully.
Run this script to validate the project structure and dependencies.

Usage:
    python verify_imports.py
    python verify_imports.py --verbose
"""

import sys
import argparse
from typing import List, Tuple


def print_success(message: str) -> None:
    """Print a success message."""
    print(f"✓ {message}")


def print_error(message: str) -> None:
    """Print an error message."""
    print(f"✗ {message}")


def print_info(message: str) -> None:
    """Print an info message."""
    print(f"ℹ {message}")


def verify_import(module_path: str, class_name: str | None = None) -> Tuple[bool, str]:
    """
    Verify that a module or class can be imported.
    
    Args:
        module_path: The module path (e.g., 'docsift.db')
        class_name: Optional class name to import from module
        
    Returns:
        Tuple of (success, message)
    """
    try:
        if class_name:
            exec(f"from {module_path} import {class_name}")
            return True, f"{module_path}.{class_name}"
        else:
            exec(f"import {module_path}")
            return True, module_path
    except ImportError as e:
        return False, f"ImportError: {e}"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def main() -> int:
    """Main verification function."""
    parser = argparse.ArgumentParser(description="Verify DocSift imports")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()
    
    print("=" * 60)
    print("DocSift Import Verification")
    print("=" * 60)
    print()
    
    # Define imports to verify
    # Format: (module_path, class_name or None, is_required)
    imports_to_verify: List[Tuple[str, str | None, bool]] = [
        # Core modules
        ("docsift", None, True),
        ("docsift._version", "__version__", True),
        
        # Core module (no external deps)
        ("docsift.core", "Document", True),
        ("docsift.core", "Collection", True),
        ("docsift.core", "Context", True),
        
        # MCP module (no external deps)
        ("docsift.mcp", "MCPServer", True),
        ("docsift.mcp", "ServerConfig", True),
        ("docsift.mcp", "ToolRegistry", True),
        ("docsift.mcp", "JsonRpcRequest", True),
        
        # CLI module (click and rich are required deps)
        ("docsift.cli.main", "cli", True),
        ("docsift.cli.main", "main", True),
        ("docsift.cli.config", "get_config", True),
        ("docsift.cli.formatters", "console", True),
    ]
    
    # Optional imports (require additional dependencies)
    optional_imports: List[Tuple[str, str | None, bool]] = [
        # Database module - requires sqlite-vec
        ("docsift.database", "DatabaseConnection", False),
        ("docsift.database", "CollectionRepository", False),
        ("docsift.database", "DocumentRepository", False),
        ("docsift.database", "ContextRepository", False),
        ("docsift.database", "MigrationManager", False),
        
        # Search module - requires structlog
        ("docsift.search", "SearchStrategy", False),
        ("docsift.search", "BM25SearchStrategy", False),
        ("docsift.search", "VectorSearchStrategy", False),
        ("docsift.search", "HybridSearchStrategy", False),
        ("docsift.search", "RRFFusion", False),
        ("docsift.search", "QueryExpansion", False),
        ("docsift.search", "Reranker", False),
        
        # Utils module - requires structlog
        ("docsift.utils", "setup_logging", False),
        ("docsift.utils", "get_data_dir", False),
        ("docsift.utils", "ProgressTracker", False),
        ("docsift.utils", "chunk_text", False),
        
        # MCP Server module - requires structlog
        ("docsift.mcp_server", "server", False),
    ]
    
    results = {
        "passed": [],
        "failed_required": [],
        "failed_optional": [],
    }
    
    # Verify required imports
    print("Verifying required imports...")
    print("-" * 60)
    
    for module_path, class_name, is_required in imports_to_verify:
        success, message = verify_import(module_path, class_name)
        full_name = f"{module_path}.{class_name}" if class_name else module_path
        
        if success:
            print_success(f"{full_name}")
            results["passed"].append(full_name)
        else:
            if is_required:
                print_error(f"{full_name} - {message}")
                results["failed_required"].append((full_name, message))
            else:
                print_info(f"{full_name} - {message} (optional)")
                results["failed_optional"].append((full_name, message))
    
    # Verify optional imports
    if args.verbose:
        print()
        print("Verifying optional imports...")
        print("-" * 60)
        
        for module_path, class_name, is_required in optional_imports:
            success, message = verify_import(module_path, class_name)
            full_name = f"{module_path}.{class_name}" if class_name else module_path
            
            if success:
                print_success(f"{full_name} (optional)")
                results["passed"].append(full_name)
            else:
                print_info(f"{full_name} - {message} (optional)")
                results["failed_optional"].append((full_name, message))
    
    # Print summary
    print()
    print("=" * 60)
    print("Verification Summary")
    print("=" * 60)
    print(f"Passed: {len(results['passed'])}")
    print(f"Failed (required): {len(results['failed_required'])}")
    print(f"Failed (optional): {len(results['failed_optional'])}")
    
    if results["failed_required"]:
        print()
        print("Required imports that failed:")
        for name, error in results["failed_required"]:
            print(f"  - {name}: {error}")
    
    print()
    
    if results["failed_required"]:
        print("❌ Verification FAILED - Some required imports could not be loaded")
        return 1
    else:
        print("✅ Verification PASSED - All required imports successful")
        return 0


if __name__ == "__main__":
    sys.exit(main())
