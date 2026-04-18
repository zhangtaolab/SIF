"""Validate code blocks in documentation."""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any

import click
import pytest
from click.testing import CliRunner

from docsift.cli.main import cli


# Files to validate
DOCS_FILES = [
    Path("README.md"),
    Path("docs/index.md"),
    Path("docs/cli-reference.md"),
    Path("docs/configuration.md"),
    Path("docs/quickstart.md"),
    Path("docs/mcp-server.md"),
    Path("docs/search-algorithms.md"),
    Path("docs/architecture.md"),
    Path("docs/models.md"),
]

# Commands that should never be executed
SKIP_COMMAND_PATTERNS = [
    "mcp http",
    "mcp daemon",
    "mcp stdio",
    "pull ",
    "index embed",
    "pip install",
    "git clone",
    "git checkout",
    "pre-commit install",
    "bench ",
]

# Commands that don't need a database
DOCSIFT_COMMANDS_NO_DB = ["--version", "--help"]

# Expected keys for JSON output examples (per D-05)
JSON_OUTPUT_SCHEMAS: dict[str, list[str]] = {
    "collection": ["id", "name", "path"],
    "document": ["id", "path", "title", "collection_id"],
    "search_result": ["document_id", "title", "path", "score"],
    "context": ["id", "type", "target", "content"],
}


def extract_code_blocks(md_path: Path) -> list[dict[str, Any]]:
    """Extract fenced code blocks from a markdown file."""
    content = md_path.read_text()
    pattern = r"```(\w*)\n(.*?)```"
    matches = re.findall(pattern, content, re.DOTALL)
    blocks = []
    for lang, block_content in matches:
        blocks.append({
            "language": lang or "text",
            "content": block_content,
            "file": md_path.name,
        })
    return blocks


def should_skip_command(cmd_line: str) -> bool:
    """Check if a command should be skipped."""
    for pattern in SKIP_COMMAND_PATTERNS:
        if pattern in cmd_line:
            return True
    # Skip exports, redirects to non-temp paths, comments
    if cmd_line.startswith("export "):
        return True
    if cmd_line.startswith("#"):
        return True
    if "> " in cmd_line and "/tmp" not in cmd_line and ">" in cmd_line.split()[0]:
        return True
    return False


def extract_shell_commands(block_content: str) -> list[str]:
    """Extract executable commands from a shell code block."""
    lines = block_content.strip().split("\n")
    commands = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("$ "):
            line = line[2:]
        if should_skip_command(line):
            continue
        commands.append(line)
    return commands


def classify_json_block(block_content: str) -> tuple[str, list[str]]:
    """Classify a JSON block and return expected keys for schema validation.

    Returns (schema_type, expected_keys) where schema_type is one of:
    - "output_example" — JSON showing command output (validate keys exist)
    - "config_example" — JSON config file (validate structure)
    - "unknown" — cannot classify
    """
    content = block_content.strip()
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return ("invalid", [])

    if not isinstance(data, dict):
        return ("unknown", [])

    keys = set(data.keys())

    # Check against known schemas
    for schema_name, expected_keys in JSON_OUTPUT_SCHEMAS.items():
        if all(k in keys for k in expected_keys):
            return (schema_name, expected_keys)

    # Check for config-like patterns
    if any(k in keys for k in ["mcpServers", "servers", "command", "args"]):
        return ("config", ["command"])

    return ("unknown", [])


class TestDocsCodeBlocks:
    """Test all code blocks in documentation."""

    def test_json_blocks_are_valid(self) -> None:
        """All JSON code blocks must be valid JSON."""
        for md_file in DOCS_FILES:
            if not md_file.exists():
                continue
            blocks = extract_code_blocks(md_file)
            for block in blocks:
                if block["language"] == "json":
                    try:
                        json.loads(block["content"])
                    except json.JSONDecodeError as e:
                        pytest.fail(f"Invalid JSON in {block['file']}: {e}")

    def test_json_output_examples_have_expected_keys(self) -> None:
        """JSON output examples must contain expected keys (per D-05)."""
        for md_file in DOCS_FILES:
            if not md_file.exists():
                continue
            blocks = extract_code_blocks(md_file)
            for block in blocks:
                if block["language"] == "json":
                    schema_type, expected_keys = classify_json_block(block["content"])
                    if schema_type in JSON_OUTPUT_SCHEMAS and expected_keys:
                        data = json.loads(block["content"])
                        missing = [k for k in expected_keys if k not in data]
                        if missing:
                            pytest.fail(
                                f"JSON output in {block['file']} missing keys: {missing}. "
                                f"Expected one of: {list(JSON_OUTPUT_SCHEMAS.keys())}"
                            )

    def test_python_blocks_are_valid_syntax(self) -> None:
        """All Python code blocks must have valid syntax."""
        for md_file in DOCS_FILES:
            if not md_file.exists():
                continue
            blocks = extract_code_blocks(md_file)
            for block in blocks:
                if block["language"] == "python":
                    content = block["content"]
                    stripped = content.strip()
                    # Skip stub/signature-only blocks (class definitions with ...)
                    if stripped.startswith("class ") and "..." in stripped and "def " not in stripped.split("...")[0]:
                        continue
                    # Skip method signature stubs with ...
                    if all(
                        line.strip().endswith("...")
                        or line.strip().endswith(":")
                        or "->" in line
                        or "@" in line.strip()
                        for line in stripped.split("\n")
                        if line.strip()
                    ):
                        continue
                    # Skip class stubs with method signatures missing bodies
                    if stripped.startswith("class "):
                        lines = stripped.split("\n")
                        is_stub = True
                        for line in lines[1:]:
                            line_stripped = line.strip()
                            if not line_stripped:
                                continue
                            if (line_stripped.endswith(":")
                                    or line_stripped.endswith("...")
                                    or "->" in line_stripped
                                    or line_stripped.startswith("@")
                                    or line_stripped.startswith("def ")
                                    or line_stripped.startswith("class ")
                                    or line_stripped == ")"
                                    or line_stripped.endswith(",")):
                                continue
                            is_stub = False
                            break
                        if is_stub:
                            continue
                    try:
                        ast.parse(content)
                    except SyntaxError as e:
                        pytest.fail(f"Invalid Python in {block['file']}: {e}")

    def test_shell_commands_exist(self, docs_runner: CliRunner) -> None:
        """Shell commands starting with 'docsift' must be valid CLI commands."""
        for md_file in DOCS_FILES:
            if not md_file.exists():
                continue
            blocks = extract_code_blocks(md_file)
            for block in blocks:
                if block["language"] in ("bash", "shell", "sh", "zsh"):
                    commands = extract_shell_commands(block["content"])
                    for cmd in commands:
                        if cmd.startswith("docsift "):
                            self._verify_docsift_command(
                                cmd, block["file"], docs_runner
                            )

    # Known CLI subcommands at each level
    _SUBCOMMANDS: dict[str, list[str]] = {
        "collection": [
            "add", "remove", "rename", "list", "show",
            "enable", "disable", "exclude", "include", "update-cmd", "ls",
        ],
        "context": ["add", "remove", "list", "prune", "rm"],
        "index": ["update", "embed", "status"],
        "search": ["search", "query", "vsearch"],
        "get": ["get", "multi-get"],
        "mcp": ["stdio", "http", "daemon"],
        "config": ["show"],
    }

    def _verify_docsift_command(
        self, cmd: str, file_name: str, runner: CliRunner
    ) -> None:
        """Verify a single docsift command exists in the CLI."""
        parts = cmd.split()
        if len(parts) < 2:
            return

        # Build help args: keep only subcommands, drop flags and positional args
        help_args = []
        i = 1  # Skip 'docsift'
        while i < len(parts):
            part = parts[i]
            if part.startswith("-"):
                # Skip flag and its value
                if i + 1 < len(parts) and not parts[i + 1].startswith("-"):
                    i += 1
            elif part in self._SUBCOMMANDS:
                help_args.append(part)
            elif any(part in subcmds for subcmds in self._SUBCOMMANDS.values()):
                help_args.append(part)
            # else: skip positional args
            i += 1

        help_args.append("--help")
        result = runner.invoke(cli, help_args)
        if result.exit_code != 0 and "No such command" in result.output:
            pytest.fail(f"Unknown command in {file_name}: {cmd}")

    def test_no_removed_commands_in_docs(self) -> None:
        """Docs must not contain removed commands."""
        removed_commands = [
            "docsift collection create",
            "docsift collection add-path",
            "docsift search similar",
            "docsift mcp start",
            "docsift mcp config",
            "docsift query ",
            "docsift embed ",
            "docsift vsearch ",
        ]
        for md_file in DOCS_FILES:
            if not md_file.exists():
                continue
            content = md_file.read_text()
            for removed in removed_commands:
                if removed in content:
                    pytest.fail(f"Removed command '{removed}' found in {md_file.name}")

    def test_model_names_are_current(self) -> None:
        """Docs must use current default model names."""
        for md_file in DOCS_FILES:
            if not md_file.exists():
                continue
            content = md_file.read_text()
            # Old model names should not appear as defaults
            if "all-MiniLM-L6-v2" in content and "Qwen" not in content:
                pytest.fail(f"Old model name in {md_file.name}")

    def test_no_bare_search_command(self) -> None:
        """Docs must not use 'docsift search <query>' without subcommand."""
        search_pattern = re.compile(r"docsift\s+search\s+(?!search\s|query\s|vsearch\s)([^-\s\"']|['\"])")
        for md_file in DOCS_FILES:
            if not md_file.exists():
                continue
            content = md_file.read_text()
            for i, line in enumerate(content.split("\n"), 1):
                if search_pattern.search(line):
                    # Skip if it's in a code block that is just showing output
                    if line.strip().startswith("$") or line.strip().startswith("#"):
                        continue
                    # Skip shell alias definitions (they contain ' but are valid)
                    if "alias " in line and "=" in line:
                        continue
                    pytest.fail(
                        f"Bare 'docsift search <query>' found in {md_file.name} line {i}: {line.strip()}"
                    )

    def test_no_positional_args_for_option_only_commands(self) -> None:
        """Commands that only take options must not have positional args in docs."""
        # index update takes no positional args
        # status takes no positional args
        for md_file in DOCS_FILES:
            if not md_file.exists():
                continue
            content = md_file.read_text()
            for i, line in enumerate(content.split("\n"), 1):
                stripped = line.strip()
                # Skip CLI reference syntax lines like "docsift index update [OPTIONS]"
                if "[OPTIONS]" in stripped:
                    continue
                if stripped.startswith("docsift index update "):
                    parts = stripped.split()
                    if len(parts) > 3 and not parts[3].startswith("-"):
                        pytest.fail(
                            f"index update with positional arg in {md_file.name} line {i}: {stripped}"
                        )
                if stripped.startswith("docsift status ") and len(stripped.split()) > 2:
                    parts = stripped.split()
                    if len(parts) > 2 and not parts[2].startswith("-"):
                        pytest.fail(
                            f"status with positional arg in {md_file.name} line {i}: {stripped}"
                        )

    def test_no_collection_delete_command(self) -> None:
        """Docs must use 'collection remove' not 'collection delete'."""
        for md_file in DOCS_FILES:
            if not md_file.exists():
                continue
            content = md_file.read_text()
            if "docsift collection delete" in content:
                pytest.fail(
                    f"Old 'collection delete' command found in {md_file.name} — use 'collection remove'"
                )

    def test_configuration_no_phantom_fields(self) -> None:
        """Verify no phantom env vars in configuration.md."""
        config_file = Path("docs/configuration.md")
        if not config_file.exists():
            pytest.skip("configuration.md not found")
        content = config_file.read_text()
        phantoms = [
            "DOCSIFT_CACHE_SIZE",
            "DOCSIFT_MAX_WORKERS",
            "DOCSIFT_LOG_FILE",
            "DOCSIFT_BM25_K1",
            "DOCSIFT_BM25_B",
            "DOCSIFT_RRF_K",
        ]
        found = [p for p in phantoms if p in content]
        if found:
            pytest.fail(f"Phantom env vars found in configuration.md: {found}")

    def test_cli_reference_has_all_commands(self) -> None:
        """Verify cli-reference.md has all commands from Click tree."""
        cli_ref = Path("docs/cli-reference.md")
        if not cli_ref.exists():
            pytest.skip("cli-reference.md not found")
        content = cli_ref.read_text()

        # Build list of expected commands from Click
        expected_commands = self._collect_click_commands()
        missing = []
        for cmd in expected_commands:
            if cmd not in content:
                missing.append(cmd)
        if missing:
            pytest.fail(f"cli-reference.md missing commands: {missing}")

    def _collect_click_commands(self) -> list[str]:
        """Collect all command paths from the Click CLI."""
        commands: list[str] = []

        def collect(group: click.Group, prefix: str = "") -> None:
            for name, cmd in group.commands.items():
                full_name = f"{prefix} {name}" if prefix else name
                commands.append(full_name)
                if isinstance(cmd, click.Group):
                    collect(cmd, full_name)

        collect(cli)
        return commands

    def test_sql_blocks_are_valid(self) -> None:
        """SQL blocks must have basic valid syntax."""
        for md_file in DOCS_FILES:
            if not md_file.exists():
                continue
            blocks = extract_code_blocks(md_file)
            for block in blocks:
                if block["language"] == "sql":
                    content = block["content"].strip().upper()
                    # Skip SQL blocks that start with comments
                    first_line = content.split("\n")[0].strip()
                    if first_line.startswith("--"):
                        # Find first non-comment line
                        for line in content.split("\n"):
                            line = line.strip()
                            if line and not line.startswith("--"):
                                first_line = line
                                break
                    if not any(
                        first_line.startswith(kw) for kw in ["CREATE", "SELECT", "INSERT", "UPDATE", "DELETE", "ALTER", "DROP"]
                    ):
                        pytest.fail(f"Invalid SQL in {block['file']}: does not start with a valid keyword")
