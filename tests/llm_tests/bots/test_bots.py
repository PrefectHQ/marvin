import pytest
from marvin.utilities.tests import assert_approx_equal


class TestBotResponse:
    @pytest.mark.parametrize(
        "message,expected_response",
        [("hello", "Greetings. How may I assist you today?")],
    )
    async def test_simple_response(self, simple_bot, message, expected_response):
        response = await simple_bot.say(message)
        assert_approx_equal(response.content, expected_response)

    async def test_memory(self, simple_bot):
        response = await simple_bot.say("My favorite color is blue")
        response = await simple_bot.say("What is my favorite color?")
        assert_approx_equal(
            response.content,
            "You told me that your favorite color is blue",
        )
