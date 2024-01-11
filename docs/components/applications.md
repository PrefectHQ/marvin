# Applications

## Overview
Marvin's `Application` uses LLMs to store and curate "state" related to the `instructions` you provide the application.

You can think of state as a JSON object that the `Application` will update as it receives new inputs relevant to the application's purpose.

## Example

```python
from marvin.beta.applications import Application

# define any functions that you want the AI to be able to call
def read_gcal() -> list[dict]:
    return [
        {
            "event": "meeting",
            "time": "tomorrow at 3pm",
            "participants": ["you", "A big Squirrel"]
        }
    ]

with Application(
    name="Marvin", tools=[read_gcal], instructions="keep track of my todos"
) as app:
    app.say("whats on my calendar? update my todos accordingly")
    # or use the chat UI
    app.chat()
```

!!! tip
    Use `Application` as a context manager to ensure that OpenAI resources are properly cleaned up.

## Context
Looking for `Application` from `marvin` 1.x? `Application` has changed a bit in `marvin` 2.x.

`Application` is now implemented as an OpenAI `Assistant`, as this allows them to process all natural language inputs by calling `tools` or updating `state` in response to the input. This enables them to track progress and contextualize interactions over time.


!!! Read
    Read more on [how Assistants work](https://platform.openai.com/docs/assistants/how-it-works) in the OpenAI docs.

Both `Assistant` and `Application` are in beta, and are subject to change. You can read the quickstart for `Assistant` [here](https://github.com/PrefectHQ/marvin/tree/main/src/marvin/beta/assistants).

