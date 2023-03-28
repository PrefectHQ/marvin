# Bots

![](bot_star_wars_hero.png)

Bots are AI assistants that can take instructions over multiple interactions. 

To create a new interactive bot, instantiate the `Bot` class with instructions, a personality, or plugins. You can begin talking to it with the `say()` method. Bots have a memory, so if you call `say()` again, the bot will recall your conversation.

!!! note
    Marvin is an async library and the `say()` method must be awaited. Bots also have a synchronous `say_sync()` method for convenience.

```python
from marvin import Bot

bot = Bot(personality='knows every Star Wars meme')

await bot.say('Hello there')
await bot.say('How do you feel about sand?')
```


By combining personalities, instructions, and plugins, you can get bots to solve complex problems that would be difficult to address in traditional code. Bots can also be exposed directly to users to act as assistants or interactive guides.

For more information about bots, see the [bot docs](bots.md).