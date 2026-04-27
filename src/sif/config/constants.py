"""Constants for SIF."""

# Application info
APP_NAME = "sif"
APP_VERSION = "0.1.0"
APP_DESCRIPTION = "A local CLI search engine for indexing and searching documents (SIF: Search / Index / Find)"

# Default paths
DEFAULT_DB_PATH = "~/.local/share/sif/sif.db"
DEFAULT_MODEL_PATH = "~/.local/share/sif/models"
DEFAULT_CONFIG_PATH = "~/.config/sif"

# Chunking defaults
DEFAULT_CHUNK_SIZE = 512
DEFAULT_CHUNK_OVERLAP = 128
MIN_CHUNK_SIZE = 100
MAX_CHUNK_SIZE = 2048

# Search defaults
DEFAULT_SEARCH_LIMIT = 10
MAX_SEARCH_LIMIT = 100
DEFAULT_BM25_K1 = 1.5
DEFAULT_BM25_B = 0.75
DEFAULT_VECTOR_WEIGHT = 0.7
DEFAULT_RRF_K = 60

# Embedding defaults
DEFAULT_EMBEDDING_DIM = 1024
DEFAULT_MAX_TOKENS = 512
DEFAULT_BATCH_SIZE = 32

# MCP server defaults
DEFAULT_MCP_HOST = "127.0.0.1"
DEFAULT_MCP_PORT = 8080
MCP_VERSION = "1.0"

# File patterns
MARKDOWN_EXTENSIONS = {".md", ".markdown", ".mdown", ".mkd", ".mkdn"}
DEFAULT_IGNORE_PATTERNS = [
    ".git",
    "__pycache__",
    "node_modules",
    ".obsidian",
    ".trash",
    "*.tmp",
    "*.temp",
]

# Database schema versions
CURRENT_SCHEMA_VERSION = 1
