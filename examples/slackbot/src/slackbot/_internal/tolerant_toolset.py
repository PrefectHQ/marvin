"""toolset wrapper that degrades to no-op if the underlying toolset can't connect.

motivation: pydantic-ai opens MCP toolsets at the start of every `agent.run()`.
when the upstream MCP server is slow to respond (cold start, transient outage),
the toolset's `__aenter__` raises a TimeoutError wrapped in nested ExceptionGroups
and the entire agent run fails. that's a bad trade for an optional toolset —
we'd rather lose access to those tools for one run than fail the whole answer.
"""

from __future__ import annotations

from typing import Any, Callable

from pydantic_ai._run_context import AgentDepsT, RunContext
from pydantic_ai.toolsets import AbstractToolset, ToolsetTool


class TolerantToolset(AbstractToolset[AgentDepsT]):
    """Wrap a toolset so that connection failures degrade to an empty toolset.

    if the inner toolset's `__aenter__` raises (e.g. MCP initialize timeout),
    `get_tools()` returns `{}` for the duration of the run and `call_tool()`
    will raise — but the agent has no tool defs so it won't try to call any.
    each new `__aenter__` re-attempts the connection, so transient failures
    don't permanently disable the toolset.
    """

    def __init__(
        self,
        inner: AbstractToolset[AgentDepsT],
        *,
        on_error: Callable[[BaseException], None] | None = None,
    ) -> None:
        self._inner = inner
        self._on_error = on_error
        self._available = False

    @property
    def id(self) -> str | None:
        return self._inner.id

    @property
    def label(self) -> str:
        return f"Tolerant({self._inner.label})"

    async def __aenter__(self) -> "TolerantToolset[AgentDepsT]":
        try:
            await self._inner.__aenter__()
            self._available = True
        except BaseException as e:  # includes ExceptionGroup from anyio task groups
            self._available = False
            if self._on_error is not None:
                self._on_error(e)
        return self

    async def __aexit__(self, *args: Any) -> bool | None:
        if not self._available:
            return None
        try:
            return await self._inner.__aexit__(*args)
        except BaseException as e:
            if self._on_error is not None:
                self._on_error(e)
            return None

    async def get_tools(
        self, ctx: RunContext[AgentDepsT]
    ) -> dict[str, ToolsetTool[AgentDepsT]]:
        if not self._available:
            return {}
        try:
            return await self._inner.get_tools(ctx)
        except BaseException as e:
            if self._on_error is not None:
                self._on_error(e)
            return {}

    async def call_tool(
        self,
        name: str,
        tool_args: dict[str, Any],
        ctx: RunContext[AgentDepsT],
        tool: ToolsetTool[AgentDepsT],
    ) -> Any:
        # only reachable when get_tools returned a non-empty dict, i.e. _available is True
        return await self._inner.call_tool(name, tool_args, ctx, tool)
