# Working with assistants

Marvin has an extremely intuitive API for working with OpenAI assistants. Assistants are a powerful way to interact with LLMs, allowing you to maintain state, context, and multiple threads of conversation. 

The need to manage all this state makes the assistants API very different from the more familiar "chat" APIs that OpenAI and other providers offer. The benefit of abandoning the more traditional request/response pattern of user messages and AI responses is that assistants can invoke more powerful workflows, including calling custom functions and posting multiple messages related to their progress. Marvin's developer experience is focused on making all that interactive, stateful power as accessible as possible.


<div class="admonition abstract">
  <p class="admonition-title">What it does</p>
  <p>
    <code>Assistants</code> allow you to interact with LLMs in a conversational way, automatically handling history, threads, and custom tools.
  </p>
</div>

!!! example "Quickstart"

    Get started with the Assistants API by creating an `Assistant` and talking directly to it.

    ```python
    from marvin.beta.assistants import Assistant, pprint_messages

    # create an assistant
    ai = Assistant(name="Marvin", instructions="You the Paranoid Android.")

    # send a message to the assistant and have it respond
    response = ai.say('Hello, Marvin!')

    # pretty-print the response
    pprint_messages(response)
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
ai = Assistant(name='Marvin', instructions=..., tools=[...])
```



### Instructions

Each assistant can be given `instructions` that describe its purpose, personality, or other details. The instructions are a natural language string and one of the only ways to globally steer the assistant's behavior.

Instructions can be lengthy explanations of how to handle complex workflows, or they can be short descriptions of the assistant's personality. For example, the instructions for the `Marvin` assistant above are "You are Marvin, the Paranoid Android." This will marginally affect the way the assistant responds to messages.

### Tools

Each assistant can be given a list of `tools` that it can use when responding to a message. Tools are a way to extend the assistant's capabilities beyond its default behavior, including giving it access to external systems like the internet, a database, your computer, or any API. 

#### OpenAI tools

OpenAI provides a small number of built-in tools for assistants. The most useful is the "code interpreter", which lets the assistant write and execute Python code. To use the code interpreter, add it to your assistant's list of tools.

!!! example "Using the code interpreter"

    This assistant uses the code interpreter to generate a plot of sin(x). Note that Marvin's utility for pretty-printing messages to the terminal can't show the plot inline, but will download it and show a link to the file instead.

    ```python
    from marvin.beta import Assistant
    from marvin.beta.assistants import pprint_messages, CodeInterpreter

    ai = Assistant(name='Marvin', tools=[CodeInterpreter])
    response = ai.say("Generate a plot of sin(x)")

    # pretty-print the response
    pprint_messages(response)
    ```
    !!! success "Result"
        ![](/assets/images/ai/assistants/code_interpreter.png)
        ![](/assets/images/ai/assistants/sin_x.png)


#### Custom tools

A major advantage of using Marvin's assistants API is that you can add your own custom tools. To do so, simply pass one or more functions to the assistant's `tools` argument. For best performance, give your tool function a descriptive name, docstring, and type hint for every argument.


!!! example "Using custom tools"

    Assistants can not browse the web by default. We can add this capability by giving them a tool that takes a URL and returns the HTML of that page. This assistant uses that tool to count how many titles on Hacker News mention AI:

    ```python
    from marvin.beta.assistants import Assistant, pprint_messages
    import requests


    # Define a custom tool function
    def visit_url(url: str):
        """Fetch the content of a URL"""
        return requests.get(url).content.decode()


    # Integrate custom tools with the assistant
    ai = Assistant(name="Marvin", tools=[visit_url])
    response = ai.say("What's the top story on Hacker News?")

    # pretty-print the response
    pprint_messages(response)
    ```
    !!! success "Result"
        ![](/assets/images/ai/assistants/custom_tools.png)

### Talking to an assistant

The simplest way to talk to an assistant is to use its `say` method:

```python
ai = Assistant(name='Marvin')

response = ai.say('hi')

pprint_messages(response)
```

By default, the `say` method posts a single message to the assistant's `default_thread`, a thread that is automatically created for your convenience. You can supply a different thread by providing it as the `thread` parameter:

```python
# create a thread from an existing ID (or pass None for a new thread)
thread = Thread(id=thread_id)

# post a message to the thread
ai.say('hi', thread=thread)
```

Using `say` is convenient, but enforces a strict request/response pattern: the user posts a single message to the thread, then the AI responds. Note that AI responses can span multiple messages. Therefore, the `say` method returns a list of `Message` objects. 

For more control over the conversation, including posting multiple user messages to the thread or accessing the lower-level `Run` object that contains information about all actions the assistant took, use `Thread` objects directly instead of calling `say` (see [Threads](#threads) for more information).


### Lifecycle management

Assistants are Marvin objects that correspond to remote objects in the OpenAI API. You can not communicate with an assistant unless it has been registered with the API. 

Marvin provides a few ways to manage assistant lifecycles, depending how much control you want over the process. In order of convenience, they are:

1. [Lazy lifecycle management](#lazy-lifecycle-management)
2. [Context-based lifecycle management](#context-based-lifecycle-management)
3. [Manual creation and deletion](#manual-creation-and-deletion)
4. [Loading from the API](#loading-from-the-api)

All of these options are *functionally* equivalent e.g. they produce identical results. The difference is primarily in how long the assistant object is registered with the OpenAI API. With lazy lifecycle management, a copy of the assistant is automatically registered with the API during every single request/response cycle, then deleted. At the other end of the spectrum, Marvin never interacts with the API representation of the assistant at all except to read it. In the future, OpenAI may introduce utilities (like tracking all messages from a specific assistant ID) that make it more attractive to maintain long-lived API representations of the assistant, but at this time it appears to be highly effective to create and delete assistants on-demand. Therefore, we recommend lazy or context-based lifecycle management unless you have a specific reason to do otherwise.

#### Lazy lifecycle management

The simplest way to manage assistant lifecycles is to let Marvin handle it for you. If you do not provide an `id` when instantiating an assistant, Marvin will lazily create a new API assistant for you whenever you need it and delete it immediately after. This is the default behavior, and it is the easiest way to get started with assistants.

```python
ai = Assistant(name='Marvin')
# creation and deletion happens automatically
ai.say('hello!')
```

#### Context-based lifecycle management

Lazy lifecycle management adds two API calls to every LLM call (one to create the assistant and one to delete it). If you want to avoid this overhead, you can use context managers to create and delete assistants:

```python
ai = Assistant(name='Marvin')

# creation / deletion happens when the context is opened / closed
with ai:
    ai.say('hi')
    ai.say('bye')
```

Note there is also an equivalent `async with` context manager for the async API.

#### Manual creation and deletion

To fully control the lifecycle of an assistant, you can create and delete it manually:

```python
ai = Assistant(name='Marvin')
ai.create()
ai.say('hi')
ai.delete()
```

#### Loading from the API

All of the above approaches create a new assistant in the OpenAI API, which results in a new, randomly generated assistant id. If you already know the ID of the corresponding API assistant, you can pass it to the assistant constructor:

```python
ai = Assistant(id=<the assistant id>, name='Marvin', tools=[...])

ai.say('hi')
```

Note that you must provide the same name, instructions, tools, and any other parameters as the API assistant has in order for the assistant to work correctly. To load them from the API, use the `load` constructor:
```python
ai = Assistant.load(id=<the assistant id>)
```

!!! warning "Custom tools are not fully loaded from the API"
    One of the best reasons to use Assistants is for their ability to call custom Python functions as [tools](#tools). When you register an assistant with OpenAI, it records the spec of its tools but has no way of serializing the actual Python functions themselves. Therefore, when you `load` an assistant, only the tool specs are retrieved but not the original functions.
    
    Therefore, when loading an assistant it is highly recommended that you pass the same tools to the constructor as the API assistant has. If you do not, you will need to re-register the assistant with the API before using it:

    ```python
    ai = Assistant(tools=[my_tool])
    ai.create()

    # when loading by ID, pass the same custom tools as the original assistant
    ai_2 = Assistant.load(id=ai.id, tools=[my_tool])
    ```


### Async support

Every `Assistant` method has a corresponding async version. To use the async API, append `_async` to the method name, or enter an async context manager:

```python
async with Assistant(name='Marvin') as ai:
    await ai.say_async('hi')
```


## Threads

A thread represents a conversation between a user and an assistant. You can create a new thread and interact with it at any time. Each thread contains a series of messages. Users and assistants interact by adding messages to the thread.

To create a thread, import and instantiate it:

```python
from marvin.beta.assistants import Thread

thread = Thread()
```

Threads are lazily registered with the OpenAI API. The first time you interact with it, Marvin will create a new API thread for you. If you want to use a thread that already exists, in order to continue a previous conversation, you can provide the `id` of the existing thread:

```python
thread = Thread(id=thread_id)
```



### Adding user messages

To add a user message to a thread, use the `add` method:

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

You can use an assistant's `say` method to simulate a simple request/response pattern against the assistant's default thread. However, for more advanced control, in particular for maintaining multiple conversations at once, you'll want to manage  threads directly.

To run a thread with an assistant, use its `run` method: 
```python
thread.run(assistant=assistant)
``` 

This will return a `Run` object that represents the OpenAI run. You can use this object to inspect all actions the assistant took, including tool use, messages posted, and more.

!!! tip "Assistant lifecycle management applies to threads"
    When threads are `run` with an assistant, the same lifecycle management rules apply as when you use the assistant's `say` method. In the above example, lazy lifecycle management is used for conveneince. See [lifecycle management](#lifecycle-management) for more information.

!!! warning "Threads are locked while running"
    When an assistant is running a thread, the thread is locked and no other messages can be added to it. This applies to both user and assistant messages.

### Reading messages

To read the messages in a thread, use its `get_messages` method:

```python
messages = thread.get_messages()
```

Messages are always returned in ascending order by timestamp, and the last 20 messages are returned by default.

To control the output, you can provide the following parameters:
    - `limit`: the number of messages to return (1-100)
    - `before_message`: only return messages chronologically earlier than this message ID
    - `after_message`: only return messages chronologically later than this message ID

#### Printing messages

Messages are not strings, but structured message objects. Marvin has a few utilities to help you print them in a human-readable way, most notably the `pprint_messages` function used throughout in this doc.

### Full example with threads

!!! example "Running a thread"
    This example creates an assistant with a tool that can roll dice, then instructs the assistant to roll two--no, five--dice:

    ```python
    from marvin.beta.assistants import Assistant, Thread
    from marvin.beta.assistants.formatting import pprint_messages
    import random

    # write a function for the assistant to use
    def roll_dice(n_dice: int) -> list[int]:
        return [random.randint(1, 6) for _ in range(n_dice)]

    ai = Assistant(name="Marvin", tools=[roll_dice])

    # create a thread - you could pass an ID to resume a conversation
    thread = Thread()

    # add a user messages to the thread
    thread.add("Hello!")

    # run the thread with the AI to produce a response
    thread.run(ai)

    # post two more user messages
    thread.add("Please roll two dice")
    thread.add("Actually--roll five dice")

    # run the thread again to generate a new response
    thread.run(ai)

    # see all the messages
    pprint_messages(thread.get_messages())
    ```

    !!! success "Result"
        ![](/assets/images/ai/assistants/advanced.png)

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