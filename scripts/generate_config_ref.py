#!/usr/bin/env python3
"""Generate configuration reference markdown from Pydantic Settings introspection."""

from __future__ import annotations

import inspect
import sys
from pathlib import Path


# Ensure the src directory is on the path so we can import docsift
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from docsift.config.settings import Settings  # noqa: E402


def get_type_name(annotation: object) -> str:
    """Return a human-readable type name from an annotation."""
    result = ""
    if annotation is None:
        result = ""
    elif isinstance(annotation, type) or hasattr(annotation, "__name__"):
        result = annotation.__name__
    elif hasattr(annotation, "__origin__"):
        origin = annotation.__origin__
        args = getattr(annotation, "__args__", ())
        if origin is type:
            result = "type"
        else:
            origin_name = getattr(origin, "__name__", str(origin))
            if args:
                arg_names = [
                    get_type_name(a) for a in args if a is not type(None)
                ]
                result = f"{origin_name}[{' | '.join(arg_names)}]" if arg_names else origin_name
            else:
                result = origin_name
    else:
        result = str(annotation)
    return result


def get_validators() -> dict[str, str]:
    """Extract field_validator methods and map them to field names."""
    validators: dict[str, str] = {}
    # Scan source for field_validator decorators
    source_lines = inspect.getsource(Settings).splitlines()
    current_field: str | None = None
    for line in source_lines:
        stripped = line.strip()
        if stripped.startswith("@field_validator("):
            inner = stripped[len("@field_validator(") : stripped.rfind(")")]
            inner = inner.strip().strip("\"'").strip()
            current_field = inner.split(",")[0].strip().strip("\"'")
        elif current_field and stripped.startswith("def "):
            method_name = stripped[4:stripped.find("(")]
            validators[current_field] = method_name
            current_field = None
    return validators


def get_computed_default(field_name: str) -> str | None:
    """Return computed default description for Path fields that default to None."""
    computed = {
        "db_path": "~/.local/share/docsift/docsift.db (computed)",
        "cache_dir": "~/.cache/docsift (computed)",
    }
    return computed.get(field_name)


SECTIONS: list[tuple[str, list[str]]] = [
    ("Application Settings", ["app_name", "debug", "log_level"]),
    ("Database Settings", ["db_path"]),
    (
        "Embedding Model Settings",
        [
            "model_name",
            "model_path",
            "embedding_dim",
            "max_tokens",
            "batch_size",
            "model_type",
            "n_gpu_layers",
        ],
    ),
    ("API Settings", ["api_key", "api_base"]),
    (
        "Reranker Settings",
        [
            "reranker_model_name",
            "reranker_model_path",
            "reranker_model_type",
            "reranker_batch_size",
        ],
    ),
    ("Chunking Settings", ["chunk_size", "chunk_overlap"]),
    ("Search Settings", ["default_search_type", "default_limit"]),
    ("MCP Server Settings", ["mcp_host", "mcp_port", "mcp_transport"]),
    ("Cache Settings", ["cache_dir", "cache_embeddings"]),
]


def _append_header(lines: list[str]) -> None:
    """Append document header and configuration methods."""
    lines.append("# Configuration")
    lines.append("")
    lines.append(
        "DocSift can be configured through environment variables or a `.env` file. "
        "This guide covers all available configuration options."
    )
    lines.append("")
    lines.append("## Configuration Methods")
    lines.append("")
    lines.append("### Environment Variables")
    lines.append("")
    lines.append("Set configuration directly in your shell:")
    lines.append("")
    lines.append("```bash")
    lines.append("export DOCSIFT_DB_PATH=/custom/path/docsift.db")
    lines.append("export DOCSIFT_LOG_LEVEL=DEBUG")
    lines.append("```")
    lines.append("")
    lines.append("### .env File")
    lines.append("")
    lines.append(
        "Create a `.env` file in your working directory or home directory:"
    )
    lines.append("")
    lines.append("```bash")
    lines.append("# ~/.env or ./.env")
    lines.append("DOCSIFT_DB_PATH=~/.local/share/docsift/docsift.db")
    lines.append("DOCSIFT_MODEL_NAME=Qwen/Qwen3-Embedding-0.6B")
    lines.append("DOCSIFT_LOG_LEVEL=INFO")
    lines.append("```")
    lines.append("")
    lines.append("### Configuration Precedence")
    lines.append("")
    lines.append("1. Environment variables (highest priority)")
    lines.append("2. `.env` file in current directory")
    lines.append("3. `.env` file in home directory")
    lines.append("4. Default values (lowest priority)")
    lines.append("")
    lines.append("## Configuration Options")
    lines.append("")


def _append_options_tables(lines: list[str]) -> None:
    """Append configuration options tables grouped by section."""
    validators = get_validators()
    model_fields = Settings.model_fields

    for section_name, field_names in SECTIONS:
        lines.append(f"### {section_name}")
        lines.append("")
        lines.append("| Variable | Type | Default | Description |")
        lines.append("|----------|------|---------|-------------|")

        for field_name in field_names:
            if field_name not in model_fields:
                continue
            field_info = model_fields[field_name]
            env_var = f"`DOCSIFT_{field_name.upper()}`"
            type_name = get_type_name(field_info.annotation)
            default = field_info.default
            if default is None:
                default = get_computed_default(field_name) or "None"
            default_str = f"`{default}`" if default != "" else '`""`'
            description = field_info.description or ""
            if field_name in validators:
                description += f" (validated by `{validators[field_name]}`)"
            lines.append(
                f"| {env_var} | {type_name} | {default_str} | {description} |"
            )

        lines.append("")


def _append_validation_rules(lines: list[str]) -> None:
    """Append validation rules section."""
    lines.append("## Validation Rules")
    lines.append("")
    lines.append(
        "DocSift validates configuration on startup. "
        "Invalid values will raise errors:"
    )
    lines.append("")
    lines.append("| Field | Rule | Error Example |")
    lines.append("|-------|------|---------------|")
    lines.append(
        "| `model_type` | Must be one of: `sentence_transformers`, `gguf`, "
        "`openai`, `modelscope`, `huggingface` | `Invalid model_type: xyz` |"
    )
    lines.append(
        "| `api_base` | Must start with `http://` or `https://` | "
        "`api_base must be an HTTP or HTTPS URL` |"
    )
    lines.append(
        "| `log_level` | Must be one of: `DEBUG`, `INFO`, `WARNING`, "
        "`ERROR`, `CRITICAL` | `Invalid log level: TRACE` |"
    )
    lines.append(
        "| `chunk_size` | Minimum 100 | "
        "`ensure this value is greater than or equal to 100` |"
    )
    lines.append(
        "| `chunk_overlap` | Minimum 0 | "
        "`ensure this value is greater than or equal to 0` |"
    )
    lines.append(
        "| `default_limit` | 1 to 100 | "
        "`ensure this value is less than or equal to 100` |"
    )
    lines.append(
        "| `mcp_port` | 1 to 65535 | "
        "`ensure this value is less than or equal to 65535` |"
    )
    lines.append("")


def _append_env_example(lines: list[str]) -> None:
    """Append complete .env example section."""
    lines.append("## Complete .env Example")
    lines.append("")
    lines.append("```bash")
    lines.append("# Database")
    lines.append("DOCSIFT_DB_PATH=~/.local/share/docsift/docsift.db")
    lines.append("")
    lines.append("# Embedding Model")
    lines.append("DOCSIFT_MODEL_NAME=Qwen/Qwen3-Embedding-0.6B")
    lines.append("DOCSIFT_EMBEDDING_DIM=1024")
    lines.append("DOCSIFT_MODEL_TYPE=sentence_transformers")
    lines.append("DOCSIFT_BATCH_SIZE=32")
    lines.append("")
    lines.append("# Reranker")
    lines.append("DOCSIFT_RERANKER_MODEL_NAME=Qwen/Qwen3-Reranker-0.6B")
    lines.append("DOCSIFT_RERANKER_MODEL_TYPE=transformers")
    lines.append("DOCSIFT_RERANKER_BATCH_SIZE=32")
    lines.append("")
    lines.append("# API (for OpenAI-compatible backends)")
    lines.append("# DOCSIFT_API_KEY=your-api-key")
    lines.append("# DOCSIFT_API_BASE=https://api.openai.com/v1")
    lines.append("")
    lines.append("# Chunking")
    lines.append("DOCSIFT_CHUNK_SIZE=512")
    lines.append("DOCSIFT_CHUNK_OVERLAP=128")
    lines.append("")
    lines.append("# Search")
    lines.append("DOCSIFT_DEFAULT_SEARCH_TYPE=hybrid")
    lines.append("DOCSIFT_DEFAULT_LIMIT=10")
    lines.append("")
    lines.append("# MCP Server")
    lines.append("DOCSIFT_MCP_HOST=127.0.0.1")
    lines.append("DOCSIFT_MCP_PORT=8080")
    lines.append("DOCSIFT_MCP_TRANSPORT=stdio")
    lines.append("")
    lines.append("# Logging")
    lines.append("DOCSIFT_LOG_LEVEL=INFO")
    lines.append("")
    lines.append("# Cache")
    lines.append("DOCSIFT_CACHE_EMBEDDINGS=true")
    lines.append("```")
    lines.append("")


def _append_validation_example(lines: list[str]) -> None:
    """Append configuration validation example section."""
    lines.append("## Configuration Validation")
    lines.append("")
    lines.append(
        "DocSift validates configuration on startup. "
        "Invalid configurations will produce errors:"
    )
    lines.append("")
    lines.append("```bash")
    lines.append("$ export DOCSIFT_MODEL_TYPE=invalid")
    lines.append("docsift collection list")
    lines.append(
        "Error: Invalid model_type: invalid. Must be one of "
        "['gguf', 'huggingface', 'modelscope', 'openai', 'sentence_transformers']"
    )
    lines.append("```")
    lines.append("")


def _append_viewing_config(lines: list[str]) -> None:
    """Append viewing current configuration section."""
    lines.append("## Viewing Current Configuration")
    lines.append("")
    lines.append("To see your current configuration:")
    lines.append("")
    lines.append("```bash")
    lines.append("# View effective configuration")
    lines.append("docsift config show")
    lines.append("")
    lines.append("# View with defaults")
    lines.append("docsift config show --with-defaults")
    lines.append("```")
    lines.append("")


def _append_best_practices(lines: list[str]) -> None:
    """Append best practices section."""
    lines.append("## Best Practices")
    lines.append("")
    lines.append(
        "1. **Use .env files**: Keep configuration in "
        "version-controlled `.env.example` files"
    )
    lines.append(
        "2. **Separate environments**: Use different databases "
        "for dev/staging/production"
    )
    lines.append(
        "3. **Monitor logs**: Set appropriate log levels for your environment"
    )
    lines.append(
        "4. **Tune chunk size**: Adjust based on your document characteristics"
    )
    lines.append(
        "5. **Cache embeddings**: Enable `DOCSIFT_CACHE_EMBEDDINGS` "
        "for repeated indexing"
    )
    lines.append("")


def _append_troubleshooting(lines: list[str]) -> None:
    """Append troubleshooting section."""
    lines.append("## Troubleshooting Configuration")
    lines.append("")
    lines.append("### Configuration Not Loading")
    lines.append("")
    lines.append("Check if the `.env` file is being read:")
    lines.append("")
    lines.append("```bash")
    lines.append("# Check file location")
    lines.append("ls -la .env ~/.env")
    lines.append("")
    lines.append("# Verify file permissions")
    lines.append("chmod 644 .env")
    lines.append("")
    lines.append("# Test with explicit path")
    lines.append("export DOCSIFT_ENV_FILE=/path/to/.env")
    lines.append("```")
    lines.append("")
    lines.append("### Environment Variables Not Applied")
    lines.append("")
    lines.append("```bash")
    lines.append("# Check if variable is set")
    lines.append("echo $DOCSIFT_LOG_LEVEL")
    lines.append("")
    lines.append("# Check in Python")
    lines.append(
        'python -c "import os; print(os.getenv(\'DOCSIFT_LOG_LEVEL\'))"'
    )
    lines.append("```")
    lines.append("")


def _append_related_docs(lines: list[str]) -> None:
    """Append related documentation links."""
    lines.append("## Related Documentation")
    lines.append("")
    lines.append("- [CLI Reference](cli-reference.md) - Command-line options")
    lines.append("- [Architecture](architecture.md) - System architecture")
    lines.append("- [Development Guide](development.md) - Development configuration")
    lines.append("")


def generate_markdown() -> str:
    """Generate the full configuration reference markdown."""
    lines: list[str] = []
    _append_header(lines)
    _append_options_tables(lines)
    _append_validation_rules(lines)
    _append_env_example(lines)
    _append_validation_example(lines)
    _append_viewing_config(lines)
    _append_best_practices(lines)
    _append_troubleshooting(lines)
    _append_related_docs(lines)
    return "\n".join(lines)


def main() -> int:
    """Generate and write configuration reference."""
    output_path = PROJECT_ROOT / "docs" / "configuration.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    markdown = generate_markdown()
    output_path.write_text(markdown, encoding="utf-8")
    sys.stderr.write(f"Generated {output_path}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
