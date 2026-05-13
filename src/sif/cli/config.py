"""Configuration management for SIF CLI."""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class CollectionConfig:
    """Configuration for a document collection."""

    name: str
    path: str
    mask: Optional[str] = None
    enabled: bool = True


@dataclass
class ContextConfig:
    """Configuration for a document context."""

    path: str
    context: str


@dataclass
class EmbedConfig:
    """Configuration for embedding settings."""

    chunk_strategy: str = "auto"  # auto, regex
    chunk_size: int = 512
    chunk_overlap: int = 50
    model: str = "default"


@dataclass
class SearchConfig:
    """Configuration for search settings."""

    default_limit: int = 10
    min_score: float = 0.0
    hybrid_weight: float = 0.5


@dataclass
class Config:
    """Main configuration class for SIF."""

    # Paths
    index_path: str = field(default_factory=lambda: str(Path.home() / ".sif" / "index.db"))
    config_path: str = field(default_factory=lambda: str(Path.home() / ".sif" / "config.json"))

    # Collections and contexts
    collections: dict[str, CollectionConfig] = field(default_factory=dict)
    contexts: dict[str, ContextConfig] = field(default_factory=dict)

    # Settings
    embed: EmbedConfig = field(default_factory=EmbedConfig)
    search: SearchConfig = field(default_factory=SearchConfig)

    # MCP settings
    mcp_port: int = 8080
    mcp_http: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "index_path": self.index_path,
            "config_path": self.config_path,
            "collections": {name: asdict(coll) for name, coll in self.collections.items()},
            "contexts": {path: asdict(ctx) for path, ctx in self.contexts.items()},
            "embed": asdict(self.embed),
            "search": asdict(self.search),
            "mcp_port": self.mcp_port,
            "mcp_http": self.mcp_http,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Config":
        """Create config from dictionary."""
        config = cls()

        if "index_path" in data:
            config.index_path = data["index_path"]
        if "config_path" in data:
            config.config_path = data["config_path"]

        # Load collections
        if "collections" in data:
            config.collections = {
                name: CollectionConfig(**coll_data)
                for name, coll_data in data["collections"].items()
            }

        # Load contexts
        if "contexts" in data:
            config.contexts = {
                path: ContextConfig(**ctx_data) for path, ctx_data in data["contexts"].items()
            }

        # Load embed config
        if "embed" in data:
            config.embed = EmbedConfig(**data["embed"])

        # Load search config
        if "search" in data:
            config.search = SearchConfig(**data["search"])

        # Load MCP settings
        if "mcp_port" in data:
            config.mcp_port = data["mcp_port"]
        if "mcp_http" in data:
            config.mcp_http = data["mcp_http"]

        return config

    def save(self, path: Optional[str] = None) -> None:
        """Save configuration to file."""
        save_path = Path(path or self.config_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)

        with open(save_path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: Optional[str] = None) -> "Config":
        """Load configuration from file."""
        config_path = Path(path or cls().config_path)

        if not config_path.exists():
            # Return default config
            config = cls()
            config.config_path = str(config_path)
            return config

        with open(config_path) as f:
            data = json.load(f)

        config = cls.from_dict(data)
        config.config_path = str(config_path)
        return config

    def add_collection(self, name: str, path: str, mask: Optional[str] = None) -> None:
        """Add a new collection."""
        self.collections[name] = CollectionConfig(name=name, path=path, mask=mask)

    def remove_collection(self, name: str) -> bool:
        """Remove a collection. Returns True if removed."""
        if name in self.collections:
            del self.collections[name]
            return True
        return False

    def rename_collection(self, old_name: str, new_name: str) -> bool:
        """Rename a collection. Returns True if renamed."""
        if old_name in self.collections and new_name not in self.collections:
            coll = self.collections.pop(old_name)
            coll.name = new_name
            self.collections[new_name] = coll
            return True
        return False

    def add_context(self, path: str, context: str) -> None:
        """Add a context for a path."""
        self.contexts[path] = ContextConfig(path=path, context=context)

    def remove_context(self, path: str) -> bool:
        """Remove a context. Returns True if removed."""
        if path in self.contexts:
            del self.contexts[path]
            return True
        return False

    def get_collection(self, name: str) -> Optional[CollectionConfig]:
        """Get a collection by name."""
        return self.collections.get(name)

    def get_context(self, path: str) -> Optional[ContextConfig]:
        """Get a context by path."""
        return self.contexts.get(path)


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config  # noqa: PLW0603
    if _config is None:
        _config = Config.load()
    return _config


def set_config(config: Config) -> None:
    """Set the global configuration instance."""
    global _config  # noqa: PLW0603
    _config = config


def reload_config(path: Optional[str] = None) -> Config:
    """Reload configuration from file."""
    global _config  # noqa: PLW0603
    _config = Config.load(path)
    return _config
