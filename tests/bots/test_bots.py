import inspect

import marvin
import pydantic
import pytest
from marvin import Bot
from marvin.bot.base import DEFAULT_INSTRUCTIONS_TEMPLATE
from marvin.bot.response_formatters import ResponseFormatter
from marvin.utilities.strings import condense_newlines, jinja_env
from marvin.utilities.types import format_type_str

custom_instructions_template = inspect.cleandoc(
    """
    Your instructions are: {{ instructions }}
    """
)


class TestCreateBots:
    async def test_create_bot_with_default_settings(self):
        bot = Bot()
        assert bot.name == condense_newlines(marvin.bot.base.DEFAULT_NAME)
        assert bot.personality == condense_newlines(marvin.bot.base.DEFAULT_PERSONALITY)
        assert bot.instructions == condense_newlines(
            marvin.bot.base.DEFAULT_INSTRUCTIONS
        )

    async def test_create_bot_with_custom_name(self):
        bot = Bot(name="Test Bot")
        assert bot.name == "Test Bot"
        assert bot.personality == condense_newlines(marvin.bot.base.DEFAULT_PERSONALITY)
        assert bot.instructions == condense_newlines(
            marvin.bot.base.DEFAULT_INSTRUCTIONS
        )

    async def test_create_bot_with_custom_personality(self):
        bot = Bot(personality="Test Personality")
        assert bot.name == marvin.bot.base.DEFAULT_NAME
        assert bot.personality == "Test Personality"
        assert bot.instructions == condense_newlines(
            marvin.bot.base.DEFAULT_INSTRUCTIONS
        )

    async def test_create_bot_with_custom_instructions(self):
        bot = Bot(instructions="Test Instructions")
        assert bot.name == marvin.bot.base.DEFAULT_NAME
        assert bot.personality == condense_newlines(marvin.bot.base.DEFAULT_PERSONALITY)
        assert bot.instructions == "Test Instructions"

    async def test_create_bot_with_custom_instruction_template(self):
        bot = Bot(
            instructions="Test Instructions",
            instructions_template=custom_instructions_template,
        )
        assert bot.name == marvin.bot.base.DEFAULT_NAME
        assert bot.personality == condense_newlines(marvin.bot.base.DEFAULT_PERSONALITY)
        assert bot.instructions == "Test Instructions"
        assert (
            jinja_env.from_string(bot.instructions_template).render(
                instructions="Test Instructions"
            )
            == "Your instructions are: Test Instructions"
        )


class TestSaveBots:
    async def test_save_bot(self):
        bot = Bot()
        await bot.save()
        loaded_bot = await Bot.load(bot.name)
        for attr in [
            "id",
            "name",
            "personality",
            "instructions",
            "plugins",
            "description",
        ]:
            assert getattr(loaded_bot, attr) == getattr(bot, attr)

    async def test_save_custom_bot(self):
        bot = Bot(
            name="Test Bot",
            personality="Test Personality",
            instructions="Test Instructions",
            description="Test Description",
        )
        await bot.save()
        loaded_bot = await Bot.load(bot.name)
        for attr in [
            "id",
            "name",
            "personality",
            "instructions",
            "plugins",
            "description",
        ]:
            assert getattr(loaded_bot, attr) == getattr(bot, attr)

    def test_save_custom_bot_sync(self):
        bot = Bot(
            name="Test Bot",
            personality="Test Personality",
            instructions="Test Instructions",
            description="Test Description",
        )
        bot.save_sync()
        loaded_bot = Bot.load_sync(bot.name)
        for attr in [
            "id",
            "name",
            "personality",
            "instructions",
            "plugins",
            "description",
        ]:
            assert getattr(loaded_bot, attr) == getattr(bot, attr)

    async def test_save_bot_with_plugins(self):
        bot = Bot(
            plugins=[
                marvin.plugins.mathematics.Calculator(),
                marvin.plugins.web.VisitURL(),
            ]
        )
        await bot.save()
        loaded_bot = await Bot.load(bot.name)
        assert loaded_bot.plugins == bot.plugins

    async def test_save_bot_with_custom_plugins(self):
        @marvin.plugin
        def my_plugin(x: int):
            """adds one to a number"""
            return x + 1

        bot = Bot(plugins=[my_plugin])
        await bot.save()
        loaded_bot = await Bot.load(bot.name)
        assert loaded_bot.plugins == bot.plugins

    async def test_save_bot_with_existing_name(self):
        await Bot().save()
        with pytest.raises(ValueError, match="(already exists)"):
            await Bot().save()

    async def test_save_bot_with_existing_custom_name(self):
        await Bot(name="abc").save()
        with pytest.raises(ValueError, match="(already exists)"):
            await Bot(name="abc").save()

    async def test_if_exists_delete(self):
        bot1 = Bot(instructions="1")
        bot2 = Bot(instructions="2")
        await bot1.save()
        await bot2.save(if_exists="delete")
        loaded_bot = await Bot.load(bot1.name)
        assert loaded_bot.instructions == bot2.instructions
        assert loaded_bot.id == bot2.id

    async def test_if_exists_update(self):
        bot1 = Bot(instructions="1")
        bot2 = Bot(instructions="2")
        await bot1.save()
        await bot2.save(if_exists="update")
        loaded_bot = await Bot.load(bot1.name)
        assert loaded_bot.instructions == bot2.instructions
        assert loaded_bot.id == bot1.id

    async def test_if_exists_cancel(self):
        bot1 = Bot(instructions="1")
        bot2 = Bot(instructions="2")
        await bot1.save()
        await bot2.save(if_exists="cancel")
        loaded_bot = await Bot.load(bot1.name)
        assert loaded_bot.instructions == bot1.instructions
        assert loaded_bot.id == bot1.id

    async def test_save_bot_with_default_instructions_template(self):
        bot = Bot(
            instructions="Test Instructions",
        )
        await bot.save()
        config = await marvin.api.bots.get_bot_config(name=bot.name)
        assert config.instructions_template is None

        loaded_bot = await Bot.load(bot.name)
        assert (
            condense_newlines(DEFAULT_INSTRUCTIONS_TEMPLATE)
            == loaded_bot.instructions_template
        )

    async def test_save_bot_with_custom_instructions_template(self):
        bot = Bot(
            instructions="Test Instructions",
            instructions_template=custom_instructions_template,
        )
        await bot.save()
        loaded_bot = await Bot.load(bot.name)
        assert (
            jinja_env.from_string(loaded_bot.instructions_template).render(
                instructions="Test Instructions"
            )
            == "Your instructions are: Test Instructions"
        )


class TestResponseFormat:
    async def test_default_response_formatter(self):
        bot = Bot()
        assert isinstance(bot.response_format, ResponseFormatter)

        assert bot.response_format.validate_response("hello") is None

    async def test_response_formatter_from_string(self):
        bot = Bot(response_format="list of strings")
        assert isinstance(
            bot.response_format, marvin.bot.response_formatters.ResponseFormatter
        )

        assert "list of strings" in bot.response_format.format

    async def test_response_formatter_from_json_string(self):
        bot = Bot(response_format="JSON list of strings")
        assert isinstance(
            bot.response_format, marvin.bot.response_formatters.JSONFormatter
        )

        assert bot.response_format.format == "JSON list of strings"

    @pytest.mark.parametrize("type_", [list, list[str], dict[str, int], int])
    async def test_response_formatter_from_python_types(self, type_):
        bot = Bot(response_format=type_)
        assert isinstance(
            bot.response_format, marvin.bot.response_formatters.TypeFormatter
        )

        assert format_type_str(type_) in bot.response_format.format

    async def test_pydantic_response_format(self):
        class OutputFormat(pydantic.BaseModel):
            x: int
            y: str = pydantic.Field(
                description=(
                    'The "written" version of the number x. For example, if x is 1,'
                    ' then y is "one".'
                )
            )

        bot = Bot(response_format=OutputFormat)
        assert isinstance(
            bot.response_format, marvin.bot.response_formatters.PydanticFormatter
        )
        assert bot.response_format.format.startswith(
            "A JSON object that satisfies the following OpenAPI schema:"
        )
        assert str(OutputFormat.schema_json()) in bot.response_format.format
