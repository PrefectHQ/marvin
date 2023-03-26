import marvin
import pydantic
import pytest
from marvin.bots.response_formatters import ResponseFormatter


class TestCreateBots:
    async def test_create_bot_with_default_settings(self):
        bot = marvin.Bot()
        assert bot.name == marvin.bots.base.DEFAULT_NAME
        assert bot.personality == marvin.bots.base.DEFAULT_PERSONALITY
        assert bot.instructions == marvin.bots.base.DEFAULT_INSTRUCTIONS

    async def test_create_bot_with_custom_name(self):
        bot = marvin.Bot(name="Test Bot")
        assert bot.name == "Test Bot"
        assert bot.personality == marvin.bots.base.DEFAULT_PERSONALITY
        assert bot.instructions == marvin.bots.base.DEFAULT_INSTRUCTIONS

    async def test_create_bot_with_custom_personality(self):
        bot = marvin.Bot(personality="Test Personality")
        assert bot.name == marvin.bots.base.DEFAULT_NAME
        assert bot.personality == "Test Personality"
        assert bot.instructions == marvin.bots.base.DEFAULT_INSTRUCTIONS

    async def test_create_bot_with_custom_instructions(self):
        bot = marvin.Bot(instructions="Test Instructions")
        assert bot.name == marvin.bots.base.DEFAULT_NAME
        assert bot.personality == marvin.bots.base.DEFAULT_PERSONALITY
        assert bot.instructions == "Test Instructions"


class TestResponseFormat:
    async def test_default_response_formatter(self):
        bot = marvin.Bot()
        assert isinstance(bot.response_format, ResponseFormatter)

        assert bot.response_format.validate_response("hello") is None

    async def test_response_formatter_from_string(self):
        bot = marvin.Bot(response_format="list of strings")
        assert isinstance(
            bot.response_format, marvin.bots.response_formatters.ResponseFormatter
        )

        assert bot.response_format.format == "list of strings"

    async def test_response_formatter_from_json_string(self):
        bot = marvin.Bot(response_format="JSON list of strings")
        assert isinstance(
            bot.response_format, marvin.bots.response_formatters.JSONFormatter
        )

        assert bot.response_format.format == "JSON list of strings"

    @pytest.mark.parametrize("type_", [list, list[str], dict[str, int], int])
    async def test_response_formatter_from_python_types(self, type_):
        bot = marvin.Bot(response_format=type_)
        assert isinstance(
            bot.response_format, marvin.bots.response_formatters.TypeFormatter
        )

        assert str(type_) in bot.response_format.format

    async def test_pydantic_response_format(self):
        class OutputFormat(pydantic.BaseModel):
            x: int
            y: str = pydantic.Field(
                description=(
                    'The "written" version of the number x. For example, if x is 1,'
                    ' then y is "one".'
                )
            )

        bot = marvin.Bot(response_format=OutputFormat)
        assert isinstance(
            bot.response_format, marvin.bots.response_formatters.PydanticFormatter
        )
        assert bot.response_format.format.startswith(
            "A JSON object that matches the following OpenAPI schema:"
        )
        assert str(OutputFormat.schema_json()) in bot.response_format.format
