# Bots

The central abstraction in Marvin is the `Bot` class. At its core, a bot is an interface for sending text to a LLM and receiving a response. Marvin allows users to customize this behavior in various ways that can transform bots from "AI assistants" to reusable programs.

## Customization 
### Name
Names are unique identifiers that make it easy to reference a specific bot.

### Instructions
Instructions define the bot's behavior by specifying how it should respond. For example, the default instructions are to assist the user. However, more utilitarian bots might be instructed to only respond with JSON (or with a specific JSON schema), extract keywords, always rhyme, etc. Bots, especially GPT-4 bots, should not go against their instructions at any time.

### Personality
Personality affects the style of the bot's responses, for example the tone, humor, how often the bot checks for confirmation, etc.

By combining personality and instructions, Bot instances can produce complex behavior that can be very different from what users might expect from a chat interface.

### Plugins
Plugins allow bots to access new information and functionality. By default, bots have plugins that let them browse the internet, visit URLs, and run simple calculations.

## Creating a bot in Python

To create a bot, instantiate the bot class. 
```python
from marvin import Bot

ford_bot = Bot(
    name="Ford", 
    personality="Can't get the hang of Thursdays", 
    instructions="Always responds as if researching an article for the Hitchhiker's Guide to the Galaxy"
)
```

You can immediately talk to the bot by calling its `say()` method, which is an async coroutine.

```python
await ford_bot.say("Hello!")
```

A synchronous convenience method is also available: `Bot.say_sync()`. 