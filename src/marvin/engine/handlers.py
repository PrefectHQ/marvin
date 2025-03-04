from marvin.engine.events import (
    ActorEndTurnEvent,
    ActorMessageDeltaEvent,
    ActorMessageEvent,
    ActorStartTurnEvent,
    EndTurnToolCallEvent,
    EndTurnToolResultEvent,
    Event,
    OrchestratorEndEvent,
    OrchestratorErrorEvent,
    OrchestratorStartEvent,
    ToolCallDeltaEvent,
    ToolCallEvent,
    ToolResultEvent,
    ToolRetryEvent,
    UserMessageEvent,
)
from marvin.utilities.logging import get_logger


class Handler:
    def __init__(self):
        self.logger = get_logger(type(self).__name__)

    def _handle(self, event: Event):
        """Called whenever an event is emitted.

        By default, it dispatches to a method named after the event type e.g.
        `self.on_{event_type}(event=event)`.

        The `on_event` method is always called for every event.
        """
        try:
            self.on_event(event=event)
            event_type = event.type.replace("-", "_")
            method = getattr(self, f"on_{event_type}", None)
            if method:
                method(event=event)
        except Exception as e:
            self.logger.error(f"Error handling event {event.type}: {e}")

    def on_event(self, event: Event):
        """Called for every event before specific handlers. Override for global event processing."""
        pass

    def on_user_message(self, event: UserMessageEvent):
        """Handles messages from the user. Called when a user sends input to the system."""
        pass

    def on_actor_message(self, event: ActorMessageEvent):
        """Handles complete messages from actors. Called when an actor produces a full response.
        This is the final event that follows any related actor_message_delta events."""
        pass

    def on_actor_message_delta(self, event: ActorMessageDeltaEvent):
        """Handles streaming updates to actor messages. Called multiple times during message generation.
        These delta events always precede the final actor_message event."""
        pass

    def on_tool_result(self, event: ToolResultEvent):
        """Handles successful tool execution results. Called when a function tool returns output.
        This is the final event in the function tool sequence, following tool_call and any tool_retry events."""
        pass

    def on_tool_retry(self, event: ToolRetryEvent):
        """Handles tool retry events. Called when a tool execution fails and needs to be retried.
        Can occur for both function tools and end turn tools before their respective final result events."""
        pass

    def on_tool_call(self, event: ToolCallEvent):
        """Handles tool call events. Called when an actor invokes a function tool.
        This follows any tool_call_delta events and precedes tool_retry or tool_result events."""
        pass

    def on_tool_call_delta(self, event: ToolCallDeltaEvent):
        """Handles streaming updates during tool call formation. Called multiple times as tool calls are generated.
        These delta events always precede either a tool_call event (for function tools) or an end_turn_tool_call event."""
        pass

    def on_end_turn_tool_call(self, event: EndTurnToolCallEvent):
        """Handles special end-of-turn tool calls. Called when actors use tools to signal turn completion.
        This event is produced instantly when an end turn tool is recognized (based on tool name).
        It follows any tool_call_delta events and precedes end_turn_tool_result or tool_retry events."""
        pass

    def on_end_turn_tool_result(self, event: EndTurnToolResultEvent):
        """Handles the final result from an end turn tool.
        This is the final event in the end turn tool sequence, following end_turn_tool_call and any tool_retry events."""
        pass

    def on_actor_start_turn(self, event: ActorStartTurnEvent):
        """Handles actor turn initiation. Called when an actor begins its processing turn."""
        pass

    def on_actor_end_turn(self, event: ActorEndTurnEvent):
        """Handles actor turn completion. Called when an actor finishes its processing turn."""
        pass

    def on_orchestrator_start(self, event: OrchestratorStartEvent):
        """Handles orchestrator initialization. Called once when orchestration begins."""
        pass

    def on_orchestrator_end(self, event: OrchestratorEndEvent):
        """Handles normal orchestrator completion. Called when orchestration ends (including after an error)."""
        pass

    def on_orchestrator_error(self, event: OrchestratorErrorEvent):
        """Handles orchestrator exceptions. Called when an error occurs during orchestration."""
        pass


class AsyncHandler:
    def __init__(self):
        self.logger = get_logger(type(self).__name__)

    async def _handle(self, event: Event):
        """Called whenever an event is emitted.

        By default, it dispatches to a method named after the event type e.g.
        `self.on_{event_type}(event=event)`.

        The `on_event` method is always called for every event.
        """
        try:
            await self.on_event(event=event)
            event_type = event.type.replace("-", "_")
            method = getattr(self, f"on_{event_type}", None)
            if method:
                await method(event=event)
        except Exception as e:
            self.logger.error(f"Error handling event {event.type}: {e}")

    async def on_event(self, event: Event):
        """Called for every event before specific handlers. Override for global event processing."""
        pass

    async def on_user_message(self, event: UserMessageEvent):
        """Handles messages from the user. Called when a user sends input to the system."""
        pass

    async def on_actor_message(self, event: ActorMessageEvent):
        """Handles complete messages from actors. Called when an actor produces a full response.
        This is the final event that follows any related actor_message_delta events."""
        pass

    async def on_actor_message_delta(self, event: ActorMessageDeltaEvent):
        """Handles streaming updates to actor messages. Called multiple times during message generation.
        These delta events always precede the final actor_message event."""
        pass

    async def on_tool_result(self, event: ToolResultEvent):
        """Handles successful tool execution results. Called when a function tool returns output.
        This is the final event in the function tool sequence, following tool_call and any tool_retry events."""
        pass

    async def on_tool_retry(self, event: ToolRetryEvent):
        """Handles tool retry events. Called when a tool execution fails and needs to be retried.
        Can occur for both function tools and end turn tools before their respective final result events."""
        pass

    async def on_tool_call(self, event: ToolCallEvent):
        """Handles tool call events. Called when an actor invokes a function tool.
        This follows any tool_call_delta events and precedes tool_retry or tool_result events."""
        pass

    async def on_tool_call_delta(self, event: ToolCallDeltaEvent):
        """Handles streaming updates during tool call formation. Called multiple times as tool calls are generated.
        These delta events always precede either a tool_call event (for function tools) or an end_turn_tool_call event."""
        pass

    async def on_end_turn_tool_call(self, event: EndTurnToolCallEvent):
        """Handles special end-of-turn tool calls. Called when actors use tools to signal turn completion.
        This event is produced instantly when an end turn tool is recognized (based on tool name).
        It follows any tool_call_delta events and precedes end_turn_tool_result or tool_retry events."""
        pass

    async def on_end_turn_tool_result(self, event: EndTurnToolResultEvent):
        """Handles the final result from an end turn tool.
        This is the final event in the end turn tool sequence, following end_turn_tool_call and any tool_retry events."""
        pass

    async def on_actor_start_turn(self, event: ActorStartTurnEvent):
        """Handles actor turn initiation. Called when an actor begins its processing turn."""
        pass

    async def on_actor_end_turn(self, event: ActorEndTurnEvent):
        """Handles actor turn completion. Called when an actor finishes its processing turn."""
        pass

    async def on_orchestrator_start(self, event: OrchestratorStartEvent):
        """Handles orchestrator initialization. Called once when orchestration begins."""
        pass

    async def on_orchestrator_end(self, event: OrchestratorEndEvent):
        """Handles normal orchestrator completion. Called when orchestration ends (including after an error)."""
        pass

    async def on_orchestrator_error(self, event: OrchestratorErrorEvent):
        """Handles orchestrator exceptions. Called when an error occurs during orchestration."""
        pass
