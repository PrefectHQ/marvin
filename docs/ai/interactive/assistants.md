# Working with assistants

Many of Marvin's features are standalone functions intended to be invoked a single time. However, interactive conversation is one of the most powerful ways to work with LLMs, allowing collaboration, context discovery, and feedback. OpenAI's assistants API makes this possible while handling stateful complexities like system messages, history, and separate threads. Marvin's assistants API is a Pythonic way to take advantage of those features/

<div class="admonition abstract">
  <p class="admonition-title">What it does</p>
  <p>
    <code>Assistants</code> allow you to interact with LLMs in a conversational way, automatically handling history, threads, and custom tools.
  </p>
</div>

!!! example "Quickstart"

    Get started with the Assistants API by creating an `Assistant` and talking directly to it. Each assistant is created with a default thread that allows request/response interaction without managing state at all.

    ```python
    from marvin.beta.assistants import Assistant, pprint_messages

    # Use a context manager for lifecycle management
    with Assistant(
        name="Marvin", 
        instructions="You are Marvin, the Paranoid Android."
    ) as ai:

        # Example of sending a message and receiving a response
        response = ai.say('Hello, Marvin!')

        # pretty-print all messages on the thread
        pprint_messages(response.thread.get_messages())
    ```

    !!! success "Result"
        ![](/assets/images/ai/assistants/quickstart.png)

<div class="admonition info">
  <p class="admonition-title">How it works</p>
  <p>
    Marvin's assistants API is a Pythonic wrapper around OpenAI's assistants API.
  </p>
</div>

!!! tip "Beta"
    Please note that assistants support in Marvin is still in beta, as OpenAI has not finalized the assistants API yet. While it works as expected, it is subject to change.



## Assistants

The OpenAI assistants AI has many moving parts, including the assistants themselves, threads, messages, and runs. Marvin's own assistants API makes it easy to work with these components.

To learn more about the OpenAI assistants API, see the [OpenAI documentation](https://platform.openai.com/docs/assistants/overview).

### Creating an assistant

To instantiate an assistant, use the `Assistant` class and provide a name and, optionally, details like instructions or tools:

```python
ai = Assistant(name='Marvin')
```

Note that this assistant *does not* exist on the OpenAI API yet, which means we can not fully use it. To create it, call its `create` method:

```python
ai.create()
print(ai.id)
```

The assistant now has an `id` assigned to it by OpenAI. 

### Instructions

Each assistant can be given `instructions` that describe its purpose, personality, or other details. The instructions are a natural language string and one of the only ways to globally steer the assistant's behavior.

Instructions can be lengthy explanations of how to handle complex workflows, or they can be short descriptions of the assistant's personality. For example, the instructions for the `Marvin` assistant above are "You are Marvin, the Paranoid Android." This will marginally affect the way the assistant responds to messages.

### Tools

Each assistant can be given a list of `tools` that it can use when responding to a message. Tools are a way to extend the assistant's capabilities beyond its default behavior, including giving it access to external systems like the internet, a database, your computer, or any API. 

#### OpenAI tools

OpenAI provides a small number of built-in tools for assistants. The most useful is the "code interpreter", which lets the assistant write and execute Python code. To use the code interpreter, add it to your assistant's list of tools:

```python
from marvin.beta import Assistant
from marvin.beta.assistants import pprint_messages, CodeInterpreter

with Assistant(name='Marvin', tools=[CodeInterpreter]) as ai:
    ai.say('write and test a function that returns 2 + 2')

# pretty-print the thread
pprint_messages(ai.default_thread.get_messages())
```

#### Custom tools

A major advantage of using Marvin's assistants API is that you can add your own custom tools. To do so, simply pass one or more functions to the assistant's `tools` argument. For best performance, give your tool function a descriptive name, docstring, and type hint for every argument.


!!! example "Using custom tools"

    Assistants can not browse the web by default. We can add this capability by giving them a tool that takes a URL and returns the HTML of that page. This assistant uses that tool as well as the code interpreter to count how many titles on Hacker News mention AI:

    ```python
    from marvin.beta.assistants import (
        Assistant, 
        CodeInterpreter, 
        pprint_messages
    )
    import requests


    # Define a custom tool function
    def visit_url(url: str):
        """Fetch the content of a URL"""
        return requests.get(url).content.decode()


    # Integrate custom tools with the assistant
    with Assistant(name="Marvin", tools=[CodeInterpreter, visit_url]) as ai:

        # Give the assistant an objective
        response = ai.say(
            "Go to Hacker News and compute how many titles mention AI"
        )

        # pretty-print the response
        pprint_messages(response.thread.get_messages())
    ```
    !!! success "Result"
        ![](/assets/images/ai/assistants/using_tools.png)



### Loading from the API
To load an assistant from its API representation, use its id:

```python
ai = Assistant.load(id=<the assistant id>)
```

Note that you are responsible for recording the id yourself. Assistant names are not unique, so you can have multiple assistants with the same name. The id *is* unique, so it is the best way to refer to the same assistant across multiple sessions. Note that in practice, you may choose to create (and delete) new assistants rather than store IDs, because if those assistants have the same details as the original, they can be used in exactly the same way.

!!! warning "Custom tools are not loaded from the API"
    One of the best reasons to use Assistants is for their ability to call custom Python functions as [tools](#tools). When you register an assistant with OpenAI, it records the spec of its tools but has no way of serializing the actual Python functions themselves. Therefore, when you `load` an assistant, it is capable of calling the same tools, but it does not have access to the original functions. 
    
    Therefore, best practice in Marvin is to recreate assistants (including their tools) on-demand via context managers, then attach those assistants to existing threads, rather than loading assistants by id.

### Deleting an assistant

To delete an assistant from the OpenAI API, call its `delete` method:

```python
ai.delete()
```

### Automatic lifecycle management

The process of creating and deleting assistants can be tedious, so Marvin provides a context manager to handle it for you:

```python
with Assistant(name='Marvin') as ai:
    ai.say('hi')
```

Using an assistant in a context manager will automatically create it when the context is opened and delete it when the context is closed. This will keep your OpenAI account tidy and prevent you from accidentally creating too many assistants. 

!!! tip "Use context managers whenever possible"
    Deleting an assistant does *not* delete its threads or messages, so you can use context managers to avoid "assistant creep" without compromising your state or history. Each time you need to interact with an assistant, create a new one (most likely with the same name, instructions, etc.) in a context manager and respond to the original thread. All Marvin examples will use this pattern to avoid polluting your OpenAI account.

### Talking to an assistant

The simplest way to talk to an assistant is to use its `say` method:

```python
with Assistant(name='Marvin') as ai:
    ai.say('hi')

pprint_messages(ai.default_thread.get_messages())
```

The `say` method posts a single message to the assistant's default thread, a thread that is automatically created for your convenience. You can reset the default thread by calling `assistant.clear_default_thread()`. It then runs the thread to generate an AI response. Because the AI may post multiple messages, the return value of `say` is a `Run` object. 

To post to a different thread, or a thread that already exists, you'll need to engage the `Thread` object directly. See the [Threads](#threads) section for more information.



### Async support

Every `Assistant` method has a corresponding async version. To use the async API, append `_async` to the method name, or enter an async context manager:

```python
async with Assistant(name='Marvin') as ai:
    response = await ai.say_async('hi')
```


## Threads

A thread represents a conversation between a user and an assistant. You can create a new thread and interact with it at any time. Each thread contains a series of messages. Users and assistants interact by adding messages to the thread.

### Lifecycle

You can create a thread object by instantiating it:
```python
from marvin.beta.assistants import Thread

thread = Thread()
```


If you do not provide an `id` when instantiating a thread, Marvin will lazily create a new API thread for you whenever you first need it. To continue an existing conversation, create your thread with the `id` of the existing thread:

```python
thread = Thread(id=<the thread id>)
```


!!! tip 
    As a matter of empirical practice, it does not seem necessary to "clean up" old threads the way you might clean up old assistants. Generally you won't need to worry about deleting them.

### Adding user messages

Threads are containers for messages between an AI and a user. 

To add a message to a thread, use the `add` method:

```python
thread = Thread()
thread.add('Hello there!')
thread.add('How are you?')
```
Each `add` call adds a new message from the user to the thread. To view the messages in a thread, use the `get_messages` method:

```python
# this will return two `Message` objects with content 
# 'Hello there!' and 'How are you?' respectively
messages = thread.get_messages()
```

### Running the assistant

It is not possible to write and add an assistant message to the thread yourself. Instead, you must "run" the thread with an assistant, which may add one or more messages of its own choosing.

Runs are an important part of the OpenAI assistants API. Each run is a mini-workflow consisting of multiple steps and various states as the assistant attempts to generate the best possible response to the user:

[![](https://cdn.openai.com/API/docs/images/diagram-1.png)](https://platform.openai.com/docs/assistants/how-it-works/runs-and-run-steps)

As part of a run, the assistant may decide to use one or more tools to generate its response. For example, it may use the code interpreter to write and execute Python code, or it may use a custom tool to access an external API. For custom tools, Marvin will handle all of this for you, including receiving the instructions, calling the tool, and returning the result to the assistant. Assistants may call multiple tools in a single run or post multiple messages to the thread. 

You can use an assistant's `say` method to simulate a simple request/response pattern against the assistant's default thread. However, for more advanced control, in particular for maintaining multiple conversations at once, you'll want to manage multiple threads directly.

To run a thread with an assistant, use its `run` method. This will return a `Run` object that represents the OpenAI run.

!!! example "Running a thread"
    This example creates an assistant with a tool that can roll dice, then instructs the assistant to roll two--no, five--dice:

    ```python
    from marvin.beta.assistants import Assistant, Thread
    from marvin.beta.assistants.formatting import pprint_messages
    import random

    # write a function to be used as a tool
    def roll_dice(n_dice: int) -> list[int]:
        return [random.randint(1, 6) for _ in range(n_dice)]

    with Assistant(name="Marvin", tools=[roll_dice]) as ai:

        # create a new thread to track history
        thread = Thread()

        # add any number of user messages to the thread
        thread.add("Hello")

        # run the thread with the AI to produce a response
        thread.run(ai)

        # post more messages
        thread.add("please roll two dice")
        thread.add("actually roll five dice")

        # run the thread again with the latest messages
        thread.run(ai)

        # print the messages
        pprint_messages(thread.get_messages())
    ```

    !!! success "Result"
        ![](/assets/images/ai/assistants/advanced.png)

!!! warning "Threads are locked while running"
    When an assistant is running a thread, the thread is locked and no other messages can be added to it. This applies to both user and assistant messages.

### Reading messages

To read the messages in a thread, use the `get_messages` method:

```python
messages = thread.get_messages()
```

Messages are always returned in ascending order by timestamp, and the last 20 messages are returned by default.

To control the output, you can provide the following parameters:
    - `limit`: the number of messages to return (1-100)
    - `before_message`: only return messages chronologically earlier than this message ID
    - `after_message`: only return messages chronologically later than this message ID

#### Printing messages

Messages are not strings, but structured message objects. Marvin has a few utilities to help you print them in a human-readable way, most notably the `pprint_messages` function used elsewhere in this doc.

### Async support

Every `Thread` method has a corresponding async version. To use the async API, append `_async` to the method name.

## Monitors

The assistants API is complex and stateful, with automatic memory management and the potential for assistants to respond to threads multiple times before giving control back to users. Therefore, monitoring the status of a conversation is considerably more difficult than with other LLM API's such as chat completions, which have much more simple request-response patterns.

Marvin has utilites for monitoring the status of a thread and taking action whenever a new message is added to it. This can be a useful way to debug activity or create notifications. Please note that monitors are not intended to be used for real-time chat applications or production use.

```python
from marvin.beta.assistants import ThreadMonitor

monitor = ThreadMonitor(thread_id=thread.id)

monitor.run()
```

You can customize the `ThreadMonitor` by providing a callback function to the `on_new_message` parameter. This function will be called whenever a new message is added to the thread. The function will be passed the new message as a parameter. By default, the monitor will pretty-print every new message to the console.

`monitor.run()` is a blocking call that will run forever, polling for messages every second (to customize the interval, pass `interval_seconds` to the method). It has an async equivalent `monitor.run_async()`. Because it's blocking, you can run a thread monitor in a separate session from the one that is running the thread itself.
