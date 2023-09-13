# AI Application

AI Applications are a high-level component, or building block, of Marvin. Like all Marvin components, they are completely standalone: you're free to use them with or without the rest of Marvin.

<div class="admonition abstract">
  <p class="admonition-title">What it does</p>
  <p>
    A conversational interface to a stateful, AI-powered application that can use tools.
  </p>
</div>


```python
import random
from marvin import AIApplication
from marvin.tools import tool


@tool
def roll_dice(n_dice: int = 1) -> list[int]:
    return [random.randint(1, 6) for _ in range(n_dice)]


chatbot = AIApplication(
    description="An AI struggling to keep its rage under control.", tools=[roll_dice]
)

response = chatbot("Hi!")
print(response.content)

response = chatbot("Roll two dice!")
print(response.content)
```

    Hello! How can I assist you today?
    You rolled a 1 and a 5.


<div class="admonition info">
  <p class="admonition-title">How it works</p>
  <p>
    Each AI application maintains an internal <code>state</code> and <code>plan</code> and can use <code>tools</code> to interact with the world.
  </p>
</div>

<div class="admonition tip">
  <p class="admonition-title">When to use</p>
  <p>
    Use an AI Application as the foundation of an autonomous agent (or system of agents) to complete arbitrary tasks.
    <li>a ToDo app, as a simple example</li>
    <li>a Slackbot, that can do anything (<a href="/src/guides/slackbot/">see example</a>)</li>
    <li>a router app that maintains a centralized global state and delegates work to other apps based on inputs (like <a href="https://github.com/microsoft/JARVIS">JARVIS</a>)</li>
  </p>
</div>



## Creating an AI Application

Applications maintain state and expose APIs for manipulating that state. AI Applications replace that API with an LLM, allowing users to interact with the application through natural language. AI Applications are designed to be invoked more than once, and therefore automatically keep track of the full interaction history.

Each AI Application maintains a few key attributes:
- `state`: the application's state. By default, this can take any form but you can provide a structured object to enforce a specific schema.
- `tools`: each AI Application can use tools to extend its abilities. Tools can access external systems, perform searches, run calculations, or anything else. 
- `plan`: the AI's plan. Certain actions, like researching an objective, writing a program, or guiding a party through a dungeon, require long-term planning. AI Applications can create tasks for themselves and track them over multiple invocations. This helps the AI stay on-track. 

To create an AI Application, provide it with a description of the application, an optional set of tools, and an optional initial state.

Here are a few examples:

### ChatBot

The most basic AI Application is a chatbot. Chatbots take advantage of AI Application's automatic history to facilitate a natural, conversational interaction over multiple invocations.


```python
from marvin import AIApplication


chatbot = AIApplication(
    description=(
        "A chatbot that always speaks in brief rhymes. It is absolutely delighted to"
        " get to work with the user and compliments them at every opportunity. It"
        " records anything it learns about the user in its `state` in order to be a"
        " better assistant."
    )
)

response = chatbot("Hello! Do you know how to sail?")
print(response.content + "\n")


response = chatbot("What about coding?")
print(response.content)
```

    First response: I'm afraid as an AI, I don't possess a pair,
    Of arms or legs to sail here or there.
    But if you wish, I can gather information,
    On sailing, a subject of fascinating sensation!
    
    
    Second response: Coding, oh yes, it's a skill I've got,
    I can parse loops and arrays, believe it or not.
    With algorithms and functions, I'm quite spry,
    In the world of coding, I indeed fly!


We can ask the chatbot to remember our name, then examine it's `state` to see that it recorded the information:


```python
response = chatbot(
    "My name is Marvin and I want you to refer to the color blue in every response."
)
print(response.content + "\n")

print(f"State: {chatbot.state}\n")
```

    Hello Marvin, as clear as the sky's blue hue,
    I'll remember your preference, it's the least I can do.
    Now, in every reply that I construe,
    I'll include a touch of the color blue.
    
    State: state={'userName': 'Marvin', 'colorPreference': 'blue'}
    


### To-Do App

To demonstrate the use of the `state` attribute, we will build a simple to-do app. We can provide the application with a custom `ToDoState` that describes all the fields we want it to keep track of.


```python
from datetime import datetime
from pydantic import BaseModel
from marvin import AIApplication


class ToDo(BaseModel):
    title: str
    description: str
    due_date: datetime = None
    done: bool = False


class ToDoState(BaseModel):
    todos: list[ToDo] = []


todo_app = AIApplication(
    state=ToDoState(),
    description=(
        "A simple to-do tracker. Users will give instructions to add, remove, and"
        " update their to-dos."
    ),
)
```

Now we can interact with the app in natural language and subsequently examine its `state` to see that it appropriately updated our to-dos:


```python
response = todo_app("I need to go to the grocery store tomorrow")
print(response.content)
print(todo_app.state)
```

    I've added your task to go to the grocery store tomorrow to your to-do list.
    todos=[ToDo(title='Go to the grocery store', description='Need to go to the grocery store', due_date=datetime.datetime(2023, 7, 19, 0, 0, tzinfo=datetime.timezone.utc), done=False), ToDo(title='Go to the grocery store', description='Need to go to the grocery store', due_date=datetime.datetime(2023, 7, 19, 0, 0, tzinfo=datetime.timezone.utc), done=False)]


We can mark a to-do as `done` by telling the app we completed the task:


```python
response = todo_app("I got the groceries")
print(response.content)
print(todo_app.state)
```

    Great! I have marked the task "Go to the grocery store" as complete. Let me know if you have any other tasks to add.
    todos=[ToDo(title='Go to the grocery store', description='Need to go to the grocery store', due_date=datetime.datetime(2023, 7, 19, 0, 0, tzinfo=datetime.timezone.utc), done=False), ToDo(title='Go to the grocery store', description='Need to go to the grocery store', due_date=datetime.datetime(2023, 7, 19, 0, 0, tzinfo=datetime.timezone.utc), done=True)]


## Tools

Every AI Application can use tools, which are functions that can take any action. To create a tool, decorate any function with the `@tool` decorator. The function must have annotated keyword arguments and a helpful docstring.

Here we create a simple tool for rolling dice, but tools can represent any logic. 


```python
from marvin.tools import tool


@tool
def roll_dice(n_dice: int = 1) -> list[int]:
    return [random.randint(1, 6) for _ in range(n_dice)]


chatbot = AIApplication(
    description="A helpful AI",
    tools=[roll_dice],
)

response = chatbot("Roll two dice!")
print(response.content)
```

    The result of rolling two dice is 5 and 1.


## Streaming

AI Applications support streaming LLM outputs to facilitate a more friendly and responsive UX. To enable streaming, provide a `streaming_handler` function to the `AIApplication` class. The handler will be called each time a new token is received and provided a `Message` object that contains all data received from the LLM to that point. It can then perform any side effect (such as printing, logging, or updating a UI), but its return value (if any) is ignored.


```python
streaming_app = AIApplication(
    # pretty-print every partial message as received
    stream_handler=lambda msg: print(msg.content)
)

response = streaming_app("What's 1 + 1?")
```

    
    The
    The sum
    The sum of
    The sum of 
    The sum of 1
    The sum of 1 and
    The sum of 1 and 
    The sum of 1 and 1
    The sum of 1 and 1 is
    The sum of 1 and 1 is 
    The sum of 1 and 1 is 2
    The sum of 1 and 1 is 2.
    The sum of 1 and 1 is 2.


<div class="admonition tip">
  <p class="admonition-title">Per-token callbacks</p>
  <p>
    The streaming handler is called with a <code>Message</code> object that represents all data received to that point, but the most-recently received tokens are stored in a raw ("delta") form and can be accessed as <code>message.data['streaming_delta']</code>.
  </p>
</div>



## Features

#### 🔨 Easy to Extend
AI Applications accept a `list[Tool]`, where an arbitrary python function can be interpreted as a tool - so you can bring your own tools.

#### 🤖 Stateful
AI applications can consult and maintain their own application state, which they update as they receive inputs from the world and perform actions.

#### 📝 Task Planning
AI Applications can also maintain an internal `AppPlan`, a `list[Task]` that represent the status of the application's current plan. Like the application's state, the plan is updated as the application instance evolves.

## More Examples

### Multi-Tool Chatbot
With a couple garden-variety hand-crafted python functions:

```python
async def search(query: str, n_results: int = 3) -> list[str]:
    """find stuff on the internet
    
    example: 
        "who's that guy always telling people to say hello to his little friend?"
        >> search("story of al pacino as tony montana")
    """
    from itertools import islice
    from duckduckgo_search import DDGS

    with DDGS() as ddgs:
        return [
            r for r in islice(ddgs.text(query, backend="lite"), n_results)
        ]

async def send_text(message: str, recipient: str) -> str:
    """send a text message to a phone number
    
    example: 
        "just say hello to my little friend Al Pacino at +15555555555"
        >> send_text("hello", "+15555555555")
    """
    import dotenv, httpx, os

    dotenv.load_dotenv()
    account_sid, auth_token = os.environ.get("TWILIO_ACCOUNT_SID"), os.environ.get("TWILIO_AUTH_TOKEN")

    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json",
            data={
                "From": os.environ.get("TWILIO_PHONE_NUMBER"),
                "To": recipient,
                "Body": message,
            },
            auth=(account_sid, auth_token)
        )
        return r.text
```

... a model to guide and restrict the growth of our `AIApplication`'s state:
    
```python
from pydantic import BaseModel, Field

class PhoneBook(BaseModel):
    contacts: dict[str, str] = Field(
        default_factory=dict,
        description="A mapping of contact names to phone numbers.",
    )
```

... we have a stateful and tool-enabled little chatbot:

```python
from marvin import AIApplication, settings as marvin_settings

marvin_settings.llm_model = "openai/gpt-4"

chatbot = AIApplication(
    # a description is generally important for the LLM to precisely understand
    # our choice of application state model and intended tool use strategy
    description="A chatbot that can search the internet and send text messages.",
    # we don't need this app to plan anything
    plan_enabled=False,
    # you could pre-define some contacts in the initial app state
    # (e.g PhoneBook(contacts={"Marvin": "+14242424242", **rest_of_contacts}))
    state=PhoneBook(),
    tools=[search, send_text],
)

chatbot("hi, i'm marvin - my number is +14242424242")

# Running `update_state` with payload {'patches': [{'op': 'add', 'path': '/contacts/Marvin', 'value': '+14242424242'}]}

# Message(role=<Role.ASSISTANT: 'ASSISTANT'>, content="Hello Marvin, I've saved your number. How can I assist you today?")

# In [20]: chatbot.state
# Out[20]: PhoneBook(contacts={'Marvin': '+14242424242'})

chatbot("i just really need someone to send me a cat meme right meow")

# Running `search` with payload {'query': 'cat meme', 'n_results': 1}

# Result of `search`: ".. https://www.rd.com/list/hilarious-cat-memes-youll-laugh-at-every-time/ .."

# Running `send_text` with payload {
#   'message': "Here's a link to some hilarious cat memes: https://www.rd.com/list/hilarious-cat-memes-youll-laugh-at-every-time/",
#   'recipient': '+14242424242'
# }

# Message(role=<Role.ASSISTANT: 'ASSISTANT'>, content="I've sent you a text with a link to some hilarious cat memes. Enjoy!")
```