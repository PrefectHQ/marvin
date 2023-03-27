# FAQ

## General

### How do I report a problem?

Please open an issue [here](https://github.com/PrefectHQ/marvin/issues/new).

## LLMs

### Should I use GPT-3.5 or GPT-4?

Marvin supports multiple LLM models. At this time, models include OpenAI's `gpt-3.5-turbo` and `gpt-4`. To set the model, use the environment variable `MARVIN_OPENAI_MODEL_NAME`.

GPT-4 improves on GPT-3.5 in a variety of ways that impact Marvin. In particular, it is much better at following instructions and staying "on-script" throughout an entire conversation. It is much less susceptible to being distracted by users and can break problems down into manageable pieces more easily. However, it is up to 30x more expensive than GPT-3.5, and is also not yet widely available to all OpenAI accounts.

For these reasons, we recommend `gpt-4` for production use but `gpt-3.5-turbo` is the default model in order to ensure that all accounts can start experimenting with Marvin right away. 

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

Why not?
