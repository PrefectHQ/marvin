# Marvin

A chatbot framework with batteries included.

> "Let’s build robots with Genuine People Personalities," they said. So they tried it out with me. I’m a personality prototype. You can tell, can’t you?
>
> -- Marvin

## Getting started

1. **Install** Marvin with `pip install marvin`

2. **Configure** an environment variable with your OpenAI API key: `export MARVIN_OPENAI_API_KEY=<your API key>`

3. **Chat** by running `marvin`. You can optionally provide your bot with a name or personality to customize the conversation:

```shell
marvin -n "Ford Prefect" -p "a roving researcher for the Hitchhiker's Guide to the Galaxy"
```


## Python API

This example shows how to configure a bot programmatically, using Marvin's async API.

```python
from marvin import Bot

bot = Bot(name='Arthur', personality='knows every Star Wars meme')

await bot.say('Hello there!')
```

## Plugins

Plugins add functionality to your bot beyond simple conversation. By default, bots have access to plugins that can search the web, visit URLs, and evaluate mathematical expressions. It's easy to add new plugins or develop your own.

```python
from marvin import Bot, Plugin

class RandomNumber(Plugin):
    def run(self, a:float, b:float) -> float:
        """Generate a random number between a and b"""
        return a + (b - a) * random.random()

bot = Bot(plugins=[RandomNumber()])

await bot.say('Use the plugin to pick a random number between 41 and 43')
```