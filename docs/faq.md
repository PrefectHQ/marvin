# FAQ


![](img/heroes/advice.png)
## General

### How do I report a problem?

Marvin is under rapid development and has a few sharp edges! If you run into trouble, please open an issue [here](https://github.com/PrefectHQ/marvin/issues/new).

### Should I use Marvin or ChatGPT?

Use both! In a true sense, Marvin *is* ChatGPT, and anything your OpenAI account has access to (including GPT-4, plugins, and more) is automatically available to Marvin as well. More specifically, Marvin is a client for ChatGPT, not an alternative to it.

ChatGPT is a powerful service primarily accessed through its own UI or by making raw API calls. Marvin provides a new way of accessing ChatGPT through a convenient library. It brings ChatGPT into your normal engineering workflow by letting you intermix Python code with AI-powered constructs that are optimized for your use case.

### Should I use GPT-4 or GPT-3.5?

Marvin supports multiple LLM models. At this time, models include OpenAI's GPT-4 (`gpt-4`) and GPT-3.5 (`gpt-3.5-turbo`). To set the model, use the environment variable `MARVIN_OPENAI_MODEL_NAME`. Because not every developer has access to GPT-4 (yet), Marvin's default model is GPT-3.5. This guarantees that everyone can use Marvin "out of the box."

Performance is much better on GPT-4 than GPT-3.5, though GPT-3.5 is still very good for many use cases. In particular, GPT-4 is better at following instructions over long interactions and staying "on-script" throughout an entire conversation. It is much less susceptible to being distracted and can break problems down into manageable pieces more easily. However, it is slower and up to 30x more expensive than GPT-3.5, and is also not yet widely available to all OpenAI accounts. Many of Marvin's prompts were originally written for GPT-3.5, which is one of the reasons the smaller model still has great results. In our experience, prompts optimized for GPT-4 usually fail outright with GPT-3.5.


## Python API
### How do I run async code?

Marvin is an async library because the vast majority of time is spent waiting for LLM responses to be returned via API. Therefore, it can be used natively in any other async library. 

The standard Python repl doesn't allow you to directly `await` async coroutines, but interpreters like [IPython](https://ipython.org/) do (IPython is included as a Marvin development dependency).

To integrate bots into synchronous frameworks, wrap async calls in `asyncio.run(coro)` or use convenience methods like `Bot.say_sync()`. Marvin uses a library called [`nest-asyncio`](https://github.com/erdewit/nest_asyncio) to run nested event loops in a way that Python doesn't usually permit.

## Marvin

### Who maintains Marvin?

Marvin is built with 💙 by [Prefect](https://www.prefect.io).

### Is Marvin open-source?

Marvin is fully open-source under an Apache 2.0 license.

### Where is Marvin's code?

Marvin's code can be found on [GitHub](https://www.github.com/prefecthq/marvin).

### Why "Marvin"?

```python
from marvin import Bot

bot = Bot()
response = await bot.say("Why are you called Marvin?")
print(response.content)

# Ah, a question of origins! The name "Marvin" might be inspired by the
# character Marvin the Paranoid Android from Douglas Adams' "The Hitchhiker's
# Guide to the Galaxy" series. Marvin the Paranoid Android was an artificially
# intelligent character with a distinct personality. However, my purpose here is
# to be a clever, fun, and helpful assistant for you. I hope I can bring a
# smile to your face while assisting you with your questions and tasks!
```

### What... is Marvin?
![](img/logos/askmarvin_mascot.jpeg){width="120" align="left"}

The first time we released an early version of Marvin in the [Prefect Slack](https://prefect.io/slack), the quality and tone of the answers was so good that some of our team became convinced that the demo was staged, with our CTO operating the Marvin account like a sock puppet. 

The idea stuck.

### Whoa code
AI functions use LLMs as a runtime and don't need any source code. We call that whoa-code.
