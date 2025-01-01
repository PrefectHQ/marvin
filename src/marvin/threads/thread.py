"""
Thread management for Marvin.

This module provides the Thread class for managing conversation context.
"""

from dataclasses import dataclass
from typing import Optional

from marvin.engine.thread import Thread as EngineThread


@dataclass(kw_only=True)
class Thread(EngineThread):
    """A conversation thread.

    This is a compatibility wrapper around the engine Thread class.
    It maintains the old interface while using the new implementation.
    """

    name: Optional[str] = None

    def __post_init__(self):
        super().__init__(
            id=getattr(self, "id", None), parent_id=getattr(self, "parent_id", None)
        )
