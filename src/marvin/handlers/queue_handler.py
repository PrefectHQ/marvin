import asyncio
from typing import Sequence

from marvin.engine.events import (
    Event,
)
from marvin.handlers.handlers import AsyncHandler


class QueueHandler(AsyncHandler):
    """
    A handler that queues events for asynchronous processing.

    QueueHandler captures events and places them into an asyncio Queue for later
    consumption. It supports filtering events based on inclusion and exclusion criteria,
    allowing for selective event processing.

    This handler is useful for:
    - Decoupling event producers from consumers
    - Implementing event buffering
    - Creating event processing pipelines
    - Selectively capturing specific event types

    Attributes:
        queue: An asyncio.Queue where events are stored
        include: Optional sequence of event types or classes to include
        exclude: Optional sequence of event types or classes to exclude
    """

    def __init__(
        self,
        queue: asyncio.Queue | None = None,
        include: Sequence[str | type[Event]] = None,
        exclude: Sequence[str | type[Event]] = None,
    ):
        """
        Initialize a QueueHandler.

        Args:
            queue: An optional asyncio.Queue to use for storing events.
                  If not provided, a new Queue will be created.
            include: An optional sequence of event types (strings) or Event classes
                    to include. If provided, only events matching these criteria
                    will be queued. If not provided, all events are included
                    (subject to exclusion rules).
            exclude: An optional sequence of event types (strings) or Event classes
                    to exclude. If provided, events matching these criteria will
                    not be queued, even if they match inclusion criteria.
        """
        super().__init__()
        self.queue = queue or asyncio.Queue()
        self.include = include or set()
        self.exclude = exclude or set()

    async def on_event(self, event: Event):
        """
        Process an event and add it to the queue if it passes filtering criteria.

        This method implements filtering logic based on the include and exclude
        parameters provided during initialization. Events are only added to the
        queue if they pass all filtering criteria.

        Args:
            event: The Event object to process

        Returns:
            None. If the event passes filtering, it is added to the queue.
            Otherwise, the method returns without adding the event.
        """
        # if an include filter is set, only include events that match the filter
        if self.include and (
            event.__class__ not in self.include or event.type not in self.include
        ):
            return
        # if an exclude filter is set, exclude events that match the filter
        if self.exclude and (
            event.__class__ in self.exclude or event.type in self.exclude
        ):
            return
        await self.queue.put(event)
