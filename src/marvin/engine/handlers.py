from marvin.engine.events import (
    AgentMessageEvent,
    Event,
    OrchestratorEndEvent,
    OrchestratorExceptionEvent,
    OrchestratorStartEvent,
    ToolCallEvent,
    ToolRetryEvent,
    ToolReturnEvent,
    UserMessageEvent,
)


class Handler:
    def handle(self, event: Event):
        """Handle is called whenever an event is emitted.

        By default, it dispatches to a method named after the event type e.g.
        `self.on_{event_type}(event=event)`.

        The `on_event` method is always called for every event.
        """
        self.on_event(event=event)
        event_type = event.type.replace("-", "_")
        method = getattr(self, f"on_{event_type}", None)
        if method:
            method(event=event)

    def on_event(self, event: Event):
        pass

    def on_user_message(self, event: UserMessageEvent):
        pass

    def on_agent_message(self, event: AgentMessageEvent):
        pass

    def on_tool_return(self, event: ToolReturnEvent):
        pass

    def on_tool_retry(self, event: ToolRetryEvent):
        pass

    def on_tool_call(self, event: ToolCallEvent):
        pass

    def on_orchestrator_start(self, event: OrchestratorStartEvent):
        pass

    def on_orchestrator_end(self, event: OrchestratorEndEvent):
        pass

    def on_orchestrator_exception(self, event: OrchestratorExceptionEvent):
        pass


class AsyncHandler:
    async def handle(self, event: Event):
        """Handle is called whenever an event is emitted.

        By default, it dispatches to a method named after the event type e.g.
        `self.on_{event_type}(event=event)`.

        The `on_event` method is always called for every event.
        """
        await self.on_event(event=event)
        event_type = event.type.replace("-", "_")
        method = getattr(self, f"on_{event_type}", None)
        if method:
            await method(event=event)

    async def on_event(self, event: Event):
        pass

    async def on_user_message(self, event: UserMessageEvent):
        pass

    async def on_agent_message(self, event: AgentMessageEvent):
        pass

    async def on_tool_return(self, event: ToolReturnEvent):
        pass

    async def on_tool_retry(self, event: ToolRetryEvent):
        pass

    async def on_tool_call(self, event: ToolCallEvent):
        pass

    async def on_orchestrator_start(self, event: OrchestratorStartEvent):
        pass

    async def on_orchestrator_end(self, event: OrchestratorEndEvent):
        pass

    async def on_orchestrator_exception(self, event: OrchestratorExceptionEvent):
        pass
