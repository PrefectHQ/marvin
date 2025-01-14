from typing import Any

import marvin


async def assert_llm_equal(result: Any, expected: Any) -> bool:
    task = marvin.Task[bool](
        name="Assert equal",
        instructions="An LLM produced the `result` value in a unit test that expected the `expected` value. Because LLM outputs can be stochastic and unpredictable, you must assess whether the `result` value is equal to the `expected` value.",
        context={
            "Result": result,
            "Expected": expected,
        },
        result_type=bool,
    )
    return await task.run_async(handlers=[])
