from pydantic_ai.usage import RunUsage
from sqlalchemy import text

from marvin.database import DBLLMCall, get_async_session
from marvin.thread import Thread


async def test_persisted_usage_and_legacy_tokens():
    thread = Thread()
    await thread.add_info_message_async("usage compatibility")
    call = await DBLLMCall.create(
        thread_id=thread.id,
        usage=RunUsage(requests=2, input_tokens=20, output_tokens=5),
        prompt_messages=[],
        completion_messages=[],
    )
    usage = await Thread(thread.id).get_usage_async()
    assert usage.requests == 2
    assert usage.input_tokens == 20
    assert usage.output_tokens == 5
    async with get_async_session() as session:
        await session.execute(
            text("UPDATE llm_calls SET usage = :usage WHERE id = :id"),
            {
                "usage": '{"requests": 3, "request_tokens": 40, "response_tokens": 7, "total_tokens": 47}',
                "id": call.id.hex,
            },
        )
        await session.commit()
    usage = await Thread(thread.id).get_usage_async()
    assert usage.requests == 3
    assert usage.input_tokens == 40
    assert usage.output_tokens == 7
