#!/usr/bin/env python3
"""
DocSift Quickstart Example

This script demonstrates the basic usage of DocSift for document indexing and search.

Prerequisites:
    pip install docsift

Usage:
    python quickstart.py

This example will:
    1. Initialize a DocSift database
    2. Add a document collection
    3. Index documents
    4. Perform searches
    5. Display results
"""

import os
import sys
import tempfile
from pathlib import Path

# Add src to path for development testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def create_sample_documents(base_path: Path) -> None:
    """Create sample documents for demonstration."""
    print("Creating sample documents...")
    
    # Create sample markdown files
    docs_dir = base_path / "documents"
    docs_dir.mkdir(exist_ok=True)
    
    # Sample document 1: Python guide
    (docs_dir / "python_guide.md").write_text("""# Python Programming Guide

## Introduction

Python is a high-level, interpreted programming language known for its simplicity
and readability. It was created by Guido van Rossum and first released in 1991.

## Key Features

- **Easy to learn**: Python has a simple syntax similar to English
- **Versatile**: Can be used for web development, data science, AI, and more
- **Large community**: Extensive libraries and frameworks available
- **Cross-platform**: Runs on Windows, macOS, and Linux

## Getting Started

To start programming in Python:

1. Install Python from python.org
2. Write your first script: `print("Hello, World!")`
3. Run it with: `python hello.py`

## Popular Libraries

- **NumPy**: Numerical computing
- **Pandas**: Data manipulation
- **Django**: Web framework
- **TensorFlow**: Machine learning
""")
    
    # Sample document 2: Machine learning intro
    (docs_dir / "ml_intro.md").write_text("""# Introduction to Machine Learning

## What is Machine Learning?

Machine Learning (ML) is a subset of artificial intelligence that enables systems
to learn and improve from experience without being explicitly programmed.

## Types of Machine Learning

### Supervised Learning
The algorithm learns from labeled training data to make predictions.
Examples: Classification, Regression

### Unsupervised Learning
The algorithm finds patterns in unlabeled data.
Examples: Clustering, Dimensionality Reduction

### Reinforcement Learning
The algorithm learns by interacting with an environment.
Examples: Game playing, Robotics

## Key Concepts

- **Features**: Input variables used for prediction
- **Labels**: Output variables we want to predict
- **Model**: The learned relationship between features and labels
- **Training**: Process of learning from data
- **Inference**: Using a trained model to make predictions

## Popular ML Frameworks

- **Scikit-learn**: General-purpose ML library
- **TensorFlow**: Deep learning framework by Google
- **PyTorch**: Deep learning framework by Meta
- **XGBoost**: Gradient boosting library
""")
    
    # Sample document 3: Database basics
    (docs_dir / "database_basics.md").write_text("""# Database Fundamentals

## What is a Database?

A database is an organized collection of data stored and accessed electronically.
Databases allow efficient storage, retrieval, and manipulation of data.

## Types of Databases

### Relational Databases (SQL)
Store data in tables with predefined relationships.
Examples: PostgreSQL, MySQL, SQLite, Oracle

### NoSQL Databases
Store data in flexible formats like documents or key-value pairs.
Examples: MongoDB, Redis, Cassandra, DynamoDB

## SQL Basics

```sql
-- Create a table
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE
);

-- Insert data
INSERT INTO users (name, email) VALUES ('Alice', 'alice@example.com');

-- Query data
SELECT * FROM users WHERE name = 'Alice';
```

## ACID Properties

- **Atomicity**: All operations succeed or none do
- **Consistency**: Database remains in a valid state
- **Isolation**: Concurrent transactions don't interfere
- **Durability**: Committed data survives failures

## Database Design

Good database design involves:
1. Normalization to reduce redundancy
2. Proper indexing for query performance
3. Choosing appropriate data types
4. Defining relationships between tables
""")
    
    print(f"  Created 3 sample documents in {docs_dir}")


def example_database_operations() -> None:
    """Demonstrate basic database operations."""
    print("\n" + "=" * 60)
    print("Example 1: Database Operations")
    print("=" * 60)
    
    try:
        from docsift.database import DatabaseConnection, MigrationManager
        
        # Create a temporary database
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name
        
        print(f"\n1. Creating database at: {db_path}")
        db = DatabaseConnection(db_path)
        
        print("2. Running migrations...")
        migrations = MigrationManager(db)
        migrations.run_migrations()
        print("   ✓ Migrations completed")
        
        print("3. Checking connection...")
        version = db.execute("SELECT sqlite_version()")[0][0]
        print(f"   ✓ SQLite version: {version}")
        
        db.close()
        os.unlink(db_path)
        print("4. Cleanup completed")
        
    except ImportError as e:
        print(f"   ✗ Import error: {e}")
        print("   Make sure DocSift is installed: pip install docsift")
    except Exception as e:
        print(f"   ✗ Error: {e}")


def example_collection_management() -> None:
    """Demonstrate collection management."""
    print("\n" + "=" * 60)
    print("Example 2: Collection Management")
    print("=" * 60)
    
    try:
        from docsift.core import Collection
        
        # Create a temporary directory for the collection
        with tempfile.TemporaryDirectory() as tmpdir:
            print(f"\n1. Creating collection from: {tmpdir}")
            
            collection = Collection(
                name="example_docs",
                path=Path(tmpdir),
                description="Example document collection"
            )
            
            print(f"   ✓ Collection created: {collection.name}")
            print(f"   ✓ Path: {collection.path}")
            print(f"   ✓ Description: {collection.description}")
            
            # Create some sample files
            (Path(tmpdir) / "doc1.md").write_text("# Sample Document 1\nContent here.")
            (Path(tmpdir) / "doc2.md").write_text("# Sample Document 2\nMore content.")
            
            print("2. Scanning for documents...")
            documents = collection.scan_documents()
            print(f"   ✓ Found {len(documents)} documents")
            
            for doc in documents:
                print(f"      - {doc.path.name}")
                
    except ImportError as e:
        print(f"   ✗ Import error: {e}")
    except Exception as e:
        print(f"   ✗ Error: {e}")


def example_search() -> None:
    """Demonstrate search functionality."""
    print("\n" + "=" * 60)
    print("Example 3: Search Operations")
    print("=" * 60)
    
    try:
        from docsift.search import BM25SearchStrategy, SearchContext
        
        print("\n1. Creating search strategy...")
        strategy = BM25SearchStrategy()
        print("   ✓ BM25 search strategy created")
        
        print("\n2. Search strategy info:")
        print(f"   - Name: {strategy.name}")
        print(f"   - Description: {strategy.description}")
        print(f"   - Requires embedding: {strategy.requires_embedding}")
        
        # Note: Actual search requires an indexed database
        print("\n3. To perform actual searches:")
        print("   - Index your documents first: docsift update")
        print("   - Then search: docsift search 'your query'")
        
    except ImportError as e:
        print(f"   ✗ Import error: {e}")
    except Exception as e:
        print(f"   ✗ Error: {e}")


def example_cli_usage() -> None:
    """Demonstrate CLI usage examples."""
    print("\n" + "=" * 60)
    print("Example 4: CLI Usage")
    print("=" * 60)
    
    print("""
Common DocSift CLI commands:

# Show help
docsift --help

# Add a collection
docsift collection add /path/to/documents --name mydocs

# List collections
docsift collection list

# Update index
docsift update

# Search documents
docsift search "machine learning"
docsift search "python tutorial" --limit 20

# Vector search
docsift vsearch "similar documents" --collection mydocs

# Get document by path
docsift get /path/to/document.md

# Check status
docsift status

# Start MCP server
docsift mcp stdio    # For Claude Desktop
docsift mcp http     # HTTP server
""")


def example_configuration() -> None:
    """Demonstrate configuration."""
    print("\n" + "=" * 60)
    print("Example 5: Configuration")
    print("=" * 60)
    
    try:
        from docsift.cli.config import Config
        
        print("\n1. Loading configuration...")
        config = Config()
        print("   ✓ Configuration loaded")
        
        print("\n2. Default configuration paths:")
        print(f"   - Config dir: {config.get_config_dir()}")
        print(f"   - Data dir: {config.get_data_dir()}")
        
        print("\n3. To customize configuration:")
        print("   - Create: ~/.config/docsift/config.yaml")
        print("   - See example_config.yaml for options")
        
    except ImportError as e:
        print(f"   ✗ Import error: {e}")
    except Exception as e:
        print(f"   ✗ Error: {e}")


def main() -> int:
    """Main function demonstrating DocSift usage."""
    print("=" * 60)
    print("DocSift Quickstart Example")
    print("=" * 60)
    print()
    print("This script demonstrates basic DocSift functionality.")
    print()
    
    # Run examples
    example_database_operations()
    example_collection_management()
    example_search()
    example_cli_usage()
    example_configuration()
    
    # Summary
    print("\n" + "=" * 60)
    print("Quickstart Complete!")
    print("=" * 60)
    print("""
Next steps:
    1. Install DocSift: pip install docsift
    2. Add a collection: docsift collection add /path/to/docs
    3. Update index: docsift update
    4. Search: docsift search "your query"

For more information:
    - Documentation: https://docsift.readthedocs.io
    - CLI help: docsift --help
    - GitHub: https://github.com/docsift/docsift
""")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
