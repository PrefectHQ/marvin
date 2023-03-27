import pytest
from marvin import Bot, plugin
from marvin.plugins.base import Plugin


@pytest.fixture
def greeting():
    @plugin
    def greeting(x):
        """Use this to get a greeting"""
        return "Hello, World!"

    return greeting


class TestPluginDecorator:
    def test_create_plugin(self, greeting):
        assert isinstance(greeting, Plugin)
        assert "Use this to get a greeting" in greeting.get_full_description()

    def test_use_plugin_with_bot(self, greeting):
        bot = Bot(plugins=[greeting])
        assert bot.plugins == [greeting]

    def test_serialize_bot_with_plugin(self, greeting):
        bot = Bot(plugins=[greeting])
        bot_dict = bot.dict()
        assert bot_dict["plugins"] == [greeting.dict()]
        assert bot_dict["plugins"][0]["discriminator"] == "greeting"

    def test_desererialize_bot_with_plugin(self, greeting):
        bot = Bot(plugins=[greeting])
        config = bot.to_bot_config()
        new_bot = Bot.from_bot_config(config)
        assert new_bot.plugins == [greeting]

    def test_cant_create_plugin_without_docstring(self):
        with pytest.raises(ValueError):

            @plugin
            def no_docstring(x):
                pass
