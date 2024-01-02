# AI Application

Looking for `AIApplication` from `marvin` 1.x?

After the release of OpenAI's Assistants API, we've decided to make `AIApplication` a type of `Assistant`.

!!! Read
    Read more on [how Assistants work](https://platform.openai.com/docs/assistants/how-it-works) in the OpenAI docs.

Both `Assistant` and `AIApplication` are in beta, and are subject to change. You can read the quickstart for `Assistant` [here](https://github.com/PrefectHQ/marvin/tree/main/src/marvin/beta/assistants).

## tl;dr

```python
from marvin.beta.assistants import Assistant

def get_weather(city: str) -> str:
    return "It's sunny!"

with Assistant(
    name="Marvin", tools=[get_weather], instructions="look up the weather for me"
) as assistant:
    assistant.say("What's the weather like in New York?")
    # or use the chat UI
    assistant.chat()
```
