import marvin


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
