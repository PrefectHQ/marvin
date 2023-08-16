# AI Components

Marvin introduces a number of components that can become the building blocks of AI-powered software.

!!! tip "Selecting a backing LLM"
    When using any of Marvin's components, the LLM used will default to the value of `MARVIN_LLM_MODEL`.
    To override this on a per-call basis, pass the `model` argument to the component's decorator.

    For example, to use `openai/gpt-3.5-turbo-16k` for an `ai_fn` call, you would do the following:

    
    ```python
    from marvin.engine.language_models.openai import OpenAIChatLLM

    @ai_fn(model=OpenAIChatLLM(model="openai/gpt-3.5-turbo-16k"))
    def my_ai_fn():
        """..."""
    ```

## AI Models

Marvin's most basic component is the AI Model, a drop-in replacement for Pydantic's `BaseModel`. AI Models can be instantiated from any string, making them ideal for structuring data, entity extraction, and synthetic data generation:



```python
from marvin import ai_model
from pydantic import BaseModel, Field


@ai_model
class Location(BaseModel):
    city: str
    state: str = Field(..., description="The two-letter state abbreviation")


Location("The Big Apple")
```




    Location(city='New York', state='NY')



## AI Classifiers

AI Classifiers let you build multi-label classifiers with no code and no training data. It enumerates your options, and uses a [clever logit bias trick](https://twitter.com/AAAzzam/status/1669753721574633473) to force an LLM to deductively choose the index of the best option given your provided input. It then returns the choice associated to that index. It's bulletproof, cost-effective, and lets you build classifiers as quickly as you can write your classes.


```python
from marvin import ai_classifier
from enum import Enum


@ai_classifier
class AppRoute(Enum):
    """Represents distinct routes command bar for a different application"""

    USER_PROFILE = "/user-profile"
    SEARCH = "/search"
    NOTIFICATIONS = "/notifications"
    SETTINGS = "/settings"
    HELP = "/help"
    CHAT = "/chat"
    DOCS = "/docs"
    PROJECTS = "/projects"
    WORKSPACES = "/workspaces"


AppRoute("update my name")
```




    <AppRoute.USER_PROFILE: '/user-profile'>



## AI Functions

AI Functions look like regular functions, but have no source code. Instead, an AI uses their description and inputs to generate their outputs, making them ideal for NLP applications like sentiment analysis. 


```python
from marvin import ai_fn


@ai_fn
def sentiment(text: str) -> float:
    """
    Given `text`, returns a number between 1 (positive) and -1 (negative)
    indicating its sentiment score.
    """


print("Text 1:", sentiment("I love working with Marvin!"))
print("Text 2:", sentiment("These examples could use some work..."))
```

    Text 1: 0.8
    Text 2: -0.2


Because AI functions are just like regular functions, you can quickly modify them for your needs. Here, we modify the above example to work with multiple strings at once:


```python
from marvin import ai_fn


@ai_fn
def sentiment_list(texts: list[str]) -> list[float]:
    """
    Given a list of `texts`, returns a list of numbers between 1 (positive) and
    -1 (negative) indicating their respective sentiment scores.
    """


sentiment_list(
    [
        "That was surprisingly easy!",
        "Oh no, not again.",
    ]
)
```




    [0.7, -0.5]



## AI Applications

AI Applications are the base class for interactive use cases. They are designed to be invoked one or more times, and automatically maintain three forms of state:

- `state`: a structured application state
- `plan`: high-level planning for the AI assistant to keep the application "on-track" across multiple invocations
- `history`: a history of all LLM interactions

AI Applications can be used to implement many "classic" LLM use cases, such as chatbots, tool-using agents, developer assistants, and more. In addition, thanks to their persistent state and planning, they can implement applications that don't have a traditional chat UX, such as a ToDo app. Here's an example:


```python
from datetime import datetime
from pydantic import BaseModel, Field
from marvin import AIApplication


# create models to represent the state of our ToDo app
class ToDo(BaseModel):
    title: str
    description: str = None
    due_date: datetime = None
    done: bool = False


class ToDoState(BaseModel):
    todos: list[ToDo] = []


# create the app with an initial state and description
todo_app = AIApplication(
    state=ToDoState(),
    description=(
        "A simple todo app. Users will provide instructions for creating and updating"
        " their todo lists."
    ),
)
```

Now we can invoke the app directly to add a to-do item. Note that the app understands that it is supposed to manipulate state, not just respond conversationally.


```python
# invoke the application by adding a todo
response = todo_app("I need to go to the store tomorrow at 5pm")


print(f"Response: {response.content}\n")
print(f"App state: {todo_app.state.json(indent=2)}")
```

    Response: Got it! I've added a new task to your to-do list. You need to go to the store tomorrow at 5pm.
    
    App state: {
      "todos": [
        {
          "title": "Go to the store",
          "description": "Buy groceries",
          "due_date": "2023-07-12T17:00:00+00:00",
          "done": false
        }
      ]
    }


We can inform the app that we already finished the task, and it updates state appropriately


```python
# complete the task
response = todo_app("I already went")


print(f"Response: {response.content}\n")
print(f"App state: {todo_app.state.json(indent=2)}")
```

    Response: Great! I've marked the task as completed. Is there anything else you'd like to add to your to-do list?
    
    App state: {
      "todos": [
        {
          "title": "Go to the store",
          "description": "Buy groceries",
          "due_date": "2023-07-12T17:00:00+00:00",
          "done": true
        }
      ]
    }

