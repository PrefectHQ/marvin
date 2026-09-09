import asyncio
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from slackbot import api


@pytest.mark.parametrize("fails", [False, True])
async def test_slow_blurb_never_delays_or_overwrites_final_status(monkeypatch, fails):
    started = asyncio.Event()
    cancelled = asyncio.Event()
    progress = SimpleNamespace(update=AsyncMock())

    async def blurb(*args):
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    result = SimpleNamespace(output="answer")

    async def answer(**kwargs):
        await started.wait()
        if fails:
            raise ValueError("answer failed")
        return result

    monkeypatch.setattr(api, "_personality_blurb", blurb)
    monkeypatch.setattr(
        api, "create_progress_message", AsyncMock(return_value=progress)
    )
    monkeypatch.setattr(api, "create_agent", lambda: SimpleNamespace(run=answer))
    monkeypatch.setattr(api, "WatchToolCalls", lambda **kwargs: nullcontext())
    monkeypatch.setattr(api, "get_run_logger", Mock())
    monkeypatch.setattr(
        api,
        "settings",
        SimpleNamespace(
            bot_model="test",
            utility_model="test",
            research_model="test",
            temperature=0,
            max_tool_calls_per_turn=5,
        ),
    )
    call = api.run_agent.fn("hello", [], {"seen_before": True}, "C1", "1.0")
    if fails:
        with pytest.raises(ValueError, match="answer failed"):
            await asyncio.wait_for(call, 1)
    else:
        assert await asyncio.wait_for(call, 1) is result
    assert cancelled.is_set()
    final = progress.update.call_args.args[0]
    assert final.startswith("❌" if fails else "✅")
