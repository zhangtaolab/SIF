"""CLI commands package."""

from sif.cli.commands.collection import collection_group
from sif.cli.commands.context import context_group
from sif.cli.commands.search import search_group
from sif.cli.commands.index import index_group
from sif.cli.commands.get import get_group
from sif.cli.commands.mcp import mcp_group

__all__ = [
    "collection_group",
    "context_group",
    "search_group",
    "index_group",
    "get_group",
    "mcp_group",
]
