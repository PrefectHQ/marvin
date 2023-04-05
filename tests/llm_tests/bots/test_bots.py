import pytest
from marvin import Bot
from marvin.utilities.tests import assert_llm


class TestBotResponse:
    @pytest.mark.parametrize(
        "message,expected_response",
        [("Say only the word 'red'", "Red")],
    )
    async def test_simple_response(self, message, expected_response):
        bot = Bot()
        response = await bot.say(message)
        assert_llm(response.content, expected_response)

    async def test_memory(self):
        bot = Bot()
        response = await bot.say("Hello, favorite color is blue")
        response = await bot.say("What is my favorite color?")
        assert_llm(
            response.content,
            "The response correctly states that the favorite color is blue.",
        )


class TestStreamingBotResponse:
    async def test_streaming_response(self):
        buffer = []
        bot = Bot()

        def callback(x):
            return buffer.append(x)

        response = await bot.say("hello!", on_token_callback=callback)

        assert len(buffer) > 1
        assert isinstance(buffer[-1], list)
        assert "".join(buffer[-1]) == response.content

    def test_streaming_response_sync(self):
        buffer = []
        bot = Bot()

        def callback(x):
            return buffer.append(x)

        response = bot.say_sync("hello!", on_token_callback=callback)

        assert len(buffer) > 1
        assert isinstance(buffer[-1], list)
        assert "".join(buffer[-1]) == response.content


class TestResponseFormatShorthand:
    async def test_int(self):
        bot = Bot(response_format=int)
        response = await bot.say("What is 1 + 1?")
        assert response.parsed_content == 2

    async def test_list_str(self):
        bot = Bot(
            instructions="solve the math problems and return only the answer",
            response_format=list[str],
        )
        response = await bot.say("Problem 1: 1 + 1\n\nProblem 2: 2 + 2")
        assert_llm(response.parsed_content, ["2", "4"])
        assert isinstance(response.parsed_content, list)
        assert all(isinstance(x, str) for x in response.parsed_content)

    async def test_natural_language_list(self):
        bot = Bot(
            instructions="solve the math problems and return only the answer",
            response_format="a list of strings",
        )
        response = await bot.say("Problem 1: 1 + 1\n\nProblem 2: 2 + 2")
        assert_llm(response.parsed_content, '["2", "4"]')

    async def test_natural_language_list_2(self):
        bot = Bot(instructions="list the keywords", response_format="a list of strings")
        response = await bot.say("The keywords are apple, banana, and cherry")
        assert response.parsed_content == '["apple", "banana", "cherry"]'

    async def test_natural_language_list_with_json_keyword(self):
        bot = Bot(
            instructions="solve the math problems and return only the answer",
            response_format="a JSON list of strings",
        )
        response = await bot.say("Problem 1: 1 + 1\n\nProblem 2: 2 + 2")
        assert_llm(response.parsed_content, ["2", "4"])
