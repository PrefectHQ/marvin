<p align="center">
  <img src="docs/img/heroes/it_hates_me_hero.png" style="width: 95%; height: auto;"/>
</p>

# Marvin

```bash
pip install marvin
```
Getting started? Head over to our [setup guide](https://www.askmarvin.ai/src/getting_started/installation/).
### The AI engineering framework

Marvin is a lightweight AI engineering framework for building natural language interfaces that are reliable, scalable, and easy to trust.

Sometimes the most challenging part of working with generative AI is remembering that it's not magic; it's software. It's new, it's nondeterministic, and it's incredibly powerful - but still software.

Marvin's goal is to bring the best practices for building dependable, observable software to generative AI. As the team behind Prefect, which does something very similar for data engineers, we've poured years of open-source developer tool experience and lessons into Marvin's design.

## Documentation
Marvin's docs are available at [askmarvin.ai](https://www.askmarvin.ai), including concepts, tutorials, and an API reference.

## Community
To ask questions, share ideas, or just chat with like-minded developers, join us on [Discord](https://discord.gg/Kgw4HpcuYG) or [Twitter](https://twitter.com/AskMarvinAI)!


## Core AI Components

Marvin's high-level abstractions are familiar Python interfaces that make it easy to leverage AI in your application. These interfaces aim to be simple and self-documenting, adding a touch of AI magic to everyday objects.

🧩 [**AI Models**](/components/ai_model) for structuring text into type-safe schemas

🏷️ [**AI Classifiers**](/components/ai_classifier) for bulletproof classification and routing

🪄 [**AI Functions**](/components/ai_function) for complex business logic and transformations

🤝 [**AI Applications**](/components/ai_application) for interactive use and persistent state

___

### 🧩 AI Models

Marvin's most basic component is the AI Model, a drop-in replacement for Pydantic's `BaseModel`. AI Models can be instantiated from any string, making them ideal for structuring data, entity extraction, and synthetic data generation. 

You can learn more about AI models [here](https://www.askmarvin.ai/components/ai_model/).

```python
from marvin import ai_model
from pydantic import BaseModel, Field


@ai_model
class Location(BaseModel):
    city: str
    state: str = Field(..., description="The two-letter state abbreviation")


Location("The Big Apple")
# Location(city='New York', state='NY')
```

### 🏷️ AI Classifiers

AI Classifiers let you build multi-label classifiers with no code and no training data. Given user input, each classifier uses a [clever logit bias trick](https://twitter.com/AAAzzam/status/1669753721574633473) to force an LLM to deductively choose the best option. It's bulletproof, cost-effective, and lets you build classifiers as quickly as you can write your classes.

You can learn more about AI Classifiers [here](https://www.askmarvin.ai/components/ai_classifier/).

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
# AppRoute.USER_PROFILE
```
### 🪄 AI Functions

AI Functions look like regular functions, but have no source code. Instead, an AI uses their description and inputs to generate their outputs, making them ideal for NLP applications like sentiment analysis. 

You can learn more about AI Functions [here](https://www.askmarvin.ai/components/ai_function/).


```python
from marvin import ai_fn


@ai_fn
def sentiment(text: str) -> float:
    """
    Given `text`, returns a number between 1 (positive) and -1 (negative)
    indicating its sentiment score.
    """


sentiment("I love working with Marvin!") # 0.8
sentiment("These examples could use some work...") # -0.2
```

### 🤝 AI Applications

AI Applications permit interactive use cases and are designed to be invoked multiple times. They maintain three forms of state: the application's own `state`, the AI's `plan`, and a `history` of interactions. AI Applications can be used to implement many "classic" LLM use cases, such as chatbots, tool-using agents, developer assistants, and more. In addition, thanks to their persistent state and planning, they can implement applications that don't have a traditional chat UX, such as a ToDo app. Here's an example:

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

# invoke the application by adding a todo
response = todo_app("I need to go to the store tomorrow at 5pm")


print(f"Response: {response.content}\n")
# Response: Got it! I've added a new task to your to-do list. You need to go to the store tomorrow at 5pm.


print(f"App state: {todo_app.state.json(indent=2)}")
# App state: {
#   "todos": [
#     {
#       "title": "Go to the store",
#       "description": "Buy groceries",
#       "due_date": "2023-07-12T17:00:00+00:00",
#       "done": false
#     }
#   ]
# }
```


## Marvin is great for...

#### Scalable APIs, data pipelines, and agents

🏷️ Build bulletproof and lightning-fast classifiers

🧩 Extract structured & type-safe data from unstructured text 

🧪 Generate synthetic data for your applications 

🫡 Solve complex deductive and inferential tasks at scale

🔎 Scrape web data without custom scrapers


#### AI powered apps with access to tools, data, and the web
😍 Customize ChatGPT with system prompts and tools

🎓 Extract relevant insights from your data

🧑‍💻 Add a junior developer to your team

🗣️ Quickly add NLP to your app

#### Coming soon...
📱 AI applications with persistent state

🕵️ Autonomous agents with high-level planning

💬 Text-to-application: generate stateful applications by describing them
