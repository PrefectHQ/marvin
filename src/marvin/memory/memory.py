import abc
import inspect
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import marvin
from marvin.utilities.logging import get_logger
from marvin.utilities.tools import update_fn

logger = get_logger("marvin.memory")


def sanitize_memory_key(key: str) -> str:
    # Remove any characters that are not alphanumeric or underscore
    return re.sub(r"[^a-zA-Z0-9_]", "", key)


@dataclass(kw_only=True)
class MemoryProvider(abc.ABC):
    def configure(self, memory_key: str) -> None:
        """Configure the provider for a specific memory."""

    @abc.abstractmethod
    def add(self, memory_key: str, content: str) -> str:
        """Create a new memory and return its ID."""

    @abc.abstractmethod
    def delete(self, memory_key: str, memory_id: str) -> None:
        """Delete a memory by its ID."""

    @abc.abstractmethod
    def search(self, memory_key: str, query: str, n: int = 20) -> dict[str, str]:
        """Search for n memories using a string query."""


@dataclass(kw_only=True)
class Memory:
    """A memory module is a partitioned collection of memories that are stored in a
    vector database, configured by a MemoryProvider.
    """

    key: str = field(kw_only=False)
    instructions: str | None = field(
        default=None,
        metadata={
            "description": "Explain what this memory is for and how it should be used.",
        },
    )
    provider: MemoryProvider = field(
        default_factory=lambda: marvin.defaults.memory_provider,
        repr=False,
    )

    def __hash__(self) -> int:
        return id(self)

    def __post_init__(self):
        # Validate key
        sanitized = sanitize_memory_key(self.key)
        if sanitized != self.key:
            raise ValueError(
                "Memory key must contain only alphanumeric characters and underscores",
            )

        # Validate and process provider
        if isinstance(self.provider, str):
            self.provider = get_memory_provider(self.provider)
        if self.provider is None:
            raise ValueError(
                inspect.cleandoc(
                    """
                    Memory modules require a MemoryProvider to configure the
                    underlying vector database. No provider was passed as an
                    argument, and no default value has been configured. 
                    
                    For more information on configuring a memory provider, see
                    the [Memory
                    documentation](https://controlflow.ai/patterns/memory), and
                    please review the [default provider
                    guide](https://controlflow.ai/guides/default-memory) for
                    information on configuring a default provider.
                    
                    Please note that if you are using ControlFlow for the first
                    time, this error is expected because ControlFlow does not include
                    vector dependencies by default.
                    """,
                ),
            )

        # Configure provider
        self.provider.configure(self.key)

    def add(self, content: str) -> str:
        return self.provider.add(self.key, content)

    def delete(self, memory_id: str) -> None:
        self.provider.delete(self.key, memory_id)

    def search(self, query: str, n: int = 20) -> dict[str, str]:
        return self.provider.search(self.key, query, n)

    def friendly_name(self) -> str:
        return f"Memory: {self.key}"

    def get_tools(self) -> list[Callable[..., Any]]:
        return [
            update_fn(
                self.add,
                name=f"store_memory_{self.key}",
                description=f"Create a new memory in {self.friendly_name()}.",
            ),
            update_fn(
                self.delete,
                name=f"delete_memory_{self.key}",
                description=f"Delete a memory by ID from {self.friendly_name()}.",
            ),
            update_fn(
                self.search,
                name=f"search_memories_{self.key}",
                description=f"Search {self.friendly_name()}. {self.instructions or ''}".rstrip(),
            ),
        ]


def get_memory_provider(provider: str) -> MemoryProvider:
    logger.debug(f"Loading memory provider: {provider}")

    # --- CHROMA ---

    if provider.startswith("chroma"):
        try:
            import chromadb  # noqa: F401
        except ImportError:
            raise ImportError(
                "To use Chroma as a memory provider, please install the `chromadb` package.",
            )

        import marvin.memory.providers.chroma as chroma_providers

        if provider == "chroma-ephemeral":
            return chroma_providers.ChromaEphemeralMemory()
        if provider == "chroma-db":
            return chroma_providers.ChromaPersistentMemory()
        if provider == "chroma-cloud":
            return chroma_providers.ChromaCloudMemory()

    # --- LanceDB ---

    elif provider.startswith("lancedb"):
        try:
            import lancedb  # noqa: F401
        except ImportError:
            raise ImportError(
                "To use LanceDB as a memory provider, please install the `lancedb` package.",
            )

        import marvin.memory.providers.lance as lance_providers

        return lance_providers.LanceMemory()

    # --- Postgres ---
    elif provider.startswith("postgres"):
        try:
            import sqlalchemy  # noqa: F401
        except ImportError:
            raise ImportError(
                "To use Postgres as a memory provider, please install the `sqlalchemy` package.",
            )

        import marvin.memory.providers.postgres as postgres_providers

        return postgres_providers.PostgresMemory()
    raise ValueError(f'Memory provider "{provider}" could not be loaded from a string.')
