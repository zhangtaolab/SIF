# Makefile for DocSift project
# Provides convenient commands for common development tasks

.PHONY: help install install-dev install-all test test-verbose lint format typecheck coverage clean build docs pre-commit security all

# Default target
help:
	@echo "DocSift Development Commands"
	@echo "============================"
	@echo ""
	@echo "Setup:"
	@echo "  make install      - Install package with basic dependencies"
	@echo "  make install-dev  - Install package with development dependencies"
	@echo "  make install-all  - Install package with all dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  make test         - Run tests with coverage"
	@echo "  make test-verbose - Run tests with verbose output"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint         - Run linting (ruff check)"
	@echo "  make format       - Format code (ruff format)"
	@echo "  make typecheck    - Run type checking (mypy)"
	@echo "  make coverage     - Generate coverage report"
	@echo "  make security     - Run security scan (bandit)"
	@echo "  make pre-commit   - Run pre-commit hooks on all files"
	@echo ""
	@echo "Build & Release:"
	@echo "  make build        - Build package distribution"
	@echo "  make clean        - Clean build artifacts"
	@echo ""
	@echo "All-in-one:"
	@echo "  make all          - Run lint, typecheck, and test"
	@echo "  make ci           - Run all CI checks locally"

# Installation targets
install:
	@echo "Installing DocSift..."
	pip install -e .

install-dev:
	@echo "Installing DocSift with development dependencies..."
	pip install -e ".[dev]"
	pre-commit install

install-all:
	@echo "Installing DocSift with all dependencies..."
	pip install -e ".[dev,all]"
	pre-commit install

# Testing targets
test:
	@echo "Running tests with coverage..."
	pytest --cov=src/docsift --cov-report=term-missing --cov-report=html --cov-report=xml

test-verbose:
	@echo "Running tests with verbose output..."
	pytest -vvs --tb=short --cov=src/docsift --cov-report=term-missing

test-fast:
	@echo "Running tests without coverage (faster)..."
	pytest -x -q

# Linting and formatting targets
lint:
	@echo "Running ruff linter..."
	ruff check .

lint-fix:
	@echo "Running ruff linter with auto-fix..."
	ruff check --fix .

format:
	@echo "Running ruff formatter..."
	ruff format .

format-check:
	@echo "Checking code formatting..."
	ruff format --check .

# Type checking target
typecheck:
	@echo "Running mypy type checker..."
	mypy src/docsift

# Coverage target
coverage:
	@echo "Generating coverage report..."
	pytest --cov=src/docsift --cov-report=html --cov-report=xml --cov-report=term-missing
	@echo "HTML report generated at: htmlcov/index.html"

# Security scan target
security:
	@echo "Running security scan with bandit..."
	bandit -r src/docsift -c pyproject.toml

# Pre-commit hooks target
pre-commit:
	@echo "Running pre-commit hooks on all files..."
	pre-commit run --all-files

# Build target
build:
	@echo "Building package..."
	python -m build
	@echo "Checking wheel contents..."
	check-wheel-contents dist/*.whl || echo "check-wheel-contents not installed, skipping"
	@echo "Checking package with twine..."
	twine check dist/* || echo "twine not installed, skipping"

# Documentation target
docs:
	@echo "Building documentation..."
	@echo "Documentation build not yet configured"

# Clean target
clean:
	@echo "Cleaning build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .eggs/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	rm -f .coverage
	rm -f coverage.xml
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	@echo "Clean complete!"

clean-all: clean
	@echo "Cleaning virtual environment..."
	rm -rf venv/
	rm -rf .venv/
	@echo "All clean complete!"

# All-in-one targets
all: lint typecheck test
	@echo "All checks passed!"

ci: format-check lint typecheck security test
	@echo "All CI checks passed!"

# Development workflow targets
dev-setup: install-dev
	@echo "Development environment setup complete!"

dev-check: format lint-fix typecheck
	@echo "Development checks complete!"

# Update dependencies
update-deps:
	@echo "Updating dependencies..."
	pip install --upgrade pip
	pip install --upgrade -e ".[dev,all]"
	pre-commit autoupdate

# Show project info
info:
	@echo "DocSift Project Information"
	@echo "==========================="
	@echo "Python version: $$(python --version)"
	@echo "Installed packages:"
	@pip list | grep -E "(docsift|ruff|mypy|pytest|black|bandit)" || true
