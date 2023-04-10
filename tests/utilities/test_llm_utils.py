import datetime
import platform

import pytest
from marvin.models.threads import Message
from marvin.utilities.llms import trim_to_context_window


@pytest.mark.parametrize(
    "messages, max_tokens, expected_result",
    [
        (
            [
                Message(role="system", content="You are an AI helper."),
                Message(role="user", content="What's the weather like?"),
                Message(role="ai", content="The weather is sunny today."),
                Message(role="user", content="What's the temperature?"),
                Message(role="ai", content="The temperature is 75°F."),
            ],
            6,
            [
                Message(role="system", content="You are an AI helper."),  # 6 tokens
            ],
        ),
        (
            [
                Message(role="system", content="You are an AI helper."),
                Message(role="user", content="What's the weather like?"),
                Message(role="ai", content="run-plugin weather --city=New York"),
                Message(
                    role="system", content="Plugin output: The weather is sunny today."
                ),
                Message(
                    role="ai",
                    content="According to my search, the weather is sunny today.",
                ),
            ],
            17,
            [
                Message(role="system", content="You are an AI helper."),  # 6 tokens
                Message(
                    role="ai",
                    content="According to my search, the weather is sunny today.",
                ),  # 11 tokens
            ],
        ),
        (
            [
                Message(role="system", content="You are an AI helper."),
                Message(role="user", content="What's the weather like?"),
                Message(role="ai", content="run-plugin weather --city=New York"),
                Message(
                    role="system", content="Plugin output: The weather is sunny today."
                ),
                Message(
                    role="ai",
                    content="According to my search, the weather is sunny today.",
                ),
            ],
            25,
            [
                Message(role="system", content="You are an AI helper."),  # 6 tokens
                Message(
                    role="ai", content="run-plugin weather --city=New York"
                ),  # 8 tokens
                Message(
                    role="ai",
                    content="According to my search, the weather is sunny today.",
                ),  # 11 tokens
            ],
        ),
        (
            [
                Message(role="system", content="You are an AI helper."),
                Message(role="user", content="What's the weather like?"),
                Message(role="ai", content="run-plugin weather --city=New York"),
                Message(
                    role="system", content="Plugin output: The weather is sunny today."
                ),
                Message(
                    role="ai",
                    content="According to my search, the weather is sunny today.",
                ),
            ],
            31,
            [
                Message(role="system", content="You are an AI helper."),  # 6 tokens
                Message(role="user", content="What's the weather like?"),  # 6 tokens
                Message(
                    role="ai", content="run-plugin weather --city=New York"
                ),  # 8 tokens
                Message(
                    role="ai",
                    content="According to my search, the weather is sunny today.",
                ),  # 11 tokens
            ],
        ),
    ],
)
def test_trim_context_window(messages, max_tokens, expected_result):
    # TIL that Windows has a different timestamp precision than unix systems
    if platform.system() == "Windows":
        messages = [
            Message(
                **msg.dict(exclude={"timestamp"}),
                timestamp=msg.timestamp + datetime.timedelta(seconds=i)
            )
            for i, msg in enumerate(messages)
        ]
        expected_result = [
            Message(
                **msg.dict(exclude={"timestamp"}),
                timestamp=msg.timestamp + datetime.timedelta(seconds=i)
            )
            for i, msg in enumerate(expected_result)
        ]

    result = trim_to_context_window(messages, max_tokens)

    excluded_attrs = {"id", "timestamp", "bot_id", "data", "thread_id"}
    assert [msg.dict(exclude=excluded_attrs) for msg in result] == [
        msg.dict(exclude=excluded_attrs) for msg in expected_result
    ]
