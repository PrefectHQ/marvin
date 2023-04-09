import pytest
from marvin.models.threads import Message
from marvin.utilities.llms import trim_context_window


@pytest.mark.parametrize(
    "messages, max_tokens, expected_result",
    [
        (  # no token context window - should be empty
            [
                Message(role="system", content="You are an AI helper."),
                Message(role="user", content="What's the weather like?"),
                Message(role="ai", content="The weather is sunny today."),
                Message(role="user", content="What's the temperature?"),
                Message(role="ai", content="The temperature is 75°F."),
            ],
            0,
            [],
        ),
        (  # only one message can fit - should prioritize first message
            [
                Message(role="system", content="You are an AI helper."),
                Message(role="user", content="What's the weather like?"),
                Message(role="ai", content="The weather is sunny today."),
                Message(role="user", content="What's the temperature?"),
                Message(role="ai", content="The temperature is 75°F."),
            ],
            10,
            [
                Message(role="system", content="You are an AI helper."),
            ],
        ),
        (  # only 2 fit - should prioritize first then last message
            [
                Message(role="system", content="You are an AI helper."),
                Message(role="user", content="What's the weather like?"),
                Message(role="ai", content="The weather is sunny today."),
                Message(role="user", content="What's the temperature?"),
                Message(role="ai", content="The temperature is 75°F."),
            ],
            17,
            [
                Message(role="system", content="You are an AI helper."),
                Message(role="ai", content="The temperature is 75°F."),
            ],
        ),
        (  # only 3 fit - same as above, but then most recent after that
            [
                Message(role="system", content="You are an AI helper."),
                Message(role="user", content="What's the weather like?"),
                Message(role="ai", content="The weather is sunny today."),
                Message(role="user", content="What's the temperature?"),
                Message(role="ai", content="The temperature is 75°F."),
            ],
            23,
            [
                Message(role="system", content="You are an AI helper."),
                Message(role="user", content="What's the temperature?"),
                Message(role="ai", content="The temperature is 75°F."),
            ],
        ),
        (
            [
                Message(role="system", content="You are an AI helper."),
                Message(role="user", content="What's the weather like?"),
                Message(role="ai", content="The weather is sunny today."),
                Message(role="user", content="What's the temperature?"),
                Message(role="ai", content="The temperature is 75°F."),
            ],
            24,
            [
                Message(role="system", content="You are an AI helper."),
                Message(role="user", content="What's the weather like?"),
                Message(role="user", content="What's the temperature?"),
                Message(role="ai", content="The temperature is 75°F."),
            ],
        ),
        (
            [
                Message(role="system", content="You are an AI helper."),
                Message(role="user", content="What's the weather like?"),
                Message(role="ai", content="The weather is sunny today."),
                Message(role="user", content="What's the temperature?"),
                Message(role="ai", content="The temperature is 75°F."),
            ],
            30,
            [
                Message(role="system", content="You are an AI helper."),
                Message(role="user", content="What's the weather like?"),
                Message(role="ai", content="The weather is sunny today."),
                Message(role="user", content="What's the temperature?"),
                Message(role="ai", content="The temperature is 75°F."),
            ],
        ),
        (  # long single message, would exceed max_tokens, cannot send
            [
                Message(role="system", content="You are an AI helper." * 10),
            ],
            30,
            [],
        ),
    ],
)
def test_trim_context_window(messages, max_tokens, expected_result):
    result = trim_context_window(messages, max_tokens)

    excluded_attrs = {"id", "timestamp", "bot_id", "data", "thread_id"}
    assert [msg.dict(exclude=excluded_attrs) for msg in result] == [
        msg.dict(exclude=excluded_attrs) for msg in expected_result
    ]
