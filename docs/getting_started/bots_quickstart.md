# Bots

To create a new interactive bot, instantiate the `Bot` class with instructions or a personality. You can being talking to it with the `say()` method. Bots have a memory, so if you call `say()` again, the bot will recall your conversation.

```python
from marvin import Bot

bot = Bot(personality='knows every Star Wars meme')

await bot.say('Hello there')
```

For more information about bots, see the [bot concept docs](bots.md).