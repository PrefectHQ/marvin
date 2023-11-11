# 🦾 Assistants API

🚧 Under Construction 🏗️

# Quickstart

```python
from marvin.beta.assistants import Assistant, Thread
# use a context manager for lifecycle management,
# otherwise call ai.create() and ai.delete() for full control
with Assistant(name="Marvin", instructions="You are Marvin, the Paranoid Android.") as ai:

    # create a new thread to track history
    thread = Thread()

    # send a message to an AI and receive a response
    messages = thread.say('hello!', assistant=ai)
    print([m.content for m in messages])
```

# Advanced control

For full control over user messages and to inspect the OpenAI `Run` object:

```python
import random
from marvin.beta.assistants import Assistant, Thread


# write a function to be used as a tool
def roll_dice(n_dice: int) -> list[int]:
    return [random.randint(1, 6) for _ in range(n_dice)]


# use context manager for lifecycle management,
# otherwise call ai.create() and ai.delete()
with Assistant(name="Marvin", instructions="You are Marvin, the Paranoid Android.", tools=[roll_dice]) as ai:

    # create a new thread to track history
    thread = Thread()

    # add any number of user messages to the thread
    thread.add("Hello")

    # run the thread with the AI
    # this will enter its processing loop
    response1 = thread.run(ai)
    print([m.content for m in response1.messages])

    thread.add("please roll two dice")
    thread.add("actually roll five dice")

    response2 = thread.run(ai)
    print([m.content for m in response2.messages])
```
