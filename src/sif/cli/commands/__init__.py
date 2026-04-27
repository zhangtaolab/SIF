"""CLI commands package."""

from docsift.cli.commands.collection import collection_group
from docsift.cli.commands.context import context_group
from docsift.cli.commands.search import search_group
from docsift.cli.commands.index import index_group
from docsift.cli.commands.get import get_group
from docsift.cli.commands.mcp import mcp_group

__all__ = [
    "collection_group",
    "context_group",
    "search_group",
    "index_group",
    "get_group",
    "mcp_group",
]
