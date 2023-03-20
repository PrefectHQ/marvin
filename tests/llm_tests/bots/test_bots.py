import pytest


class TestBotResponse:
    @pytest.mark.parametrize(
        "message,expected_response",
        [("hello", "Greetings. How may I assist you today?")],
    )
    async def test_simple_response(self, simple_bot, message, expected_response):
        response = await simple_bot.say(message)
        assert response.content == expected_response

    async def test_memory(self, simple_bot):
        response = await simple_bot.say("My favorite color is blue")
        response = await simple_bot.say("What is my favorite color?")
        assert (
            response.content
            == "You just told me that your favorite color is blue! Is that still"
            " correct?"
        )
