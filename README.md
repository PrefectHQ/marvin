#  Marvin 🤖💬

Chatbots, no assembly required.

> "Let’s build robots with Genuine People Personalities," they said. So they tried it out with me. I’m a personality prototype. You can tell, can’t you?
>
> -- Marvin

## Highlights

🤖 Custom bots with names, personalities, and instructions

🔋 Batteries included - get up and running instantly

🔌 Plugin system so bots can use software 

💬 Persistent threads with multiple bots

📡 Powered by ChatGPT (GPT-3.5) or GPT-4

🌈 ChromaDB for vector search

🐍 Async Python API

🖥️ Interactive chat CLI

⚡️ FastAPI REST API

## Getting started

Launching a bot is simple! All you need is this library and a valid [OpenAI API key](https://platform.openai.com/account/api-keys). 

1. **Install** Marvin by running `pip install marvin`

2. **Configure** your OpenAI API key as an environment variable: `export OPENAI_API_KEY=<your API key>`

3. **Chat** in your CLI by running `marvin chat`. You can *optionally* provide a name or personality to customize the conversation:

```shell
marvin chat -p "knows every Star Wars meme" Hello there
```
<img width="1034" alt="image" src="https://user-images.githubusercontent.com/153965/226232390-c98ffee3-c272-42fa-befb-70d94bebfda7.png">


## Python API

This example shows how to configure a bot programmatically, using Marvin's async API.

```python
from marvin import Bot

bot = Bot(name='Arthur', personality='knows every Star Wars meme')

await bot.say('Hello there')
```

## Rest API

Launch the Marvin REST server by running `marvin server start`. You can visit `http://localhost:4200` to view the API documentation.

## UI

*Coming soon...*
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
