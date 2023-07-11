# Marvin

### The AI engineering framework

Marvin is a lightweight framework for building AI-powered software that's reliable, scalable, and easy to trust. It's designed primarily for AI engineers: users who want to deploy cutting-edge AI to build powerful new features and applications.

Marvin is ergonomic and opinionated at every layer, but also incrementally adoptable so you can use it as much or as little as you like. It’s a Swiss Army Knife, not a kitchen sink. It’s familiar. It feels like the library you’d write if you had the time: simple, accessible, portable LLM abstractions that you can quickly deploy in your application, whether you’re doing straightforward NLP or building a full-featured autonomous agent.

Marvin prioritizes a developer experience focused on speed and reliability. It's built with type-safety and observability as first-class citizens. Its abstractions are Pythonic, simple, and self-documenting.

We're constantly meeting with developers, engineers, founders, and investors to identify the best practices and design patterns that are having the most impact. AI engineering is a rapidly developing field. We ship thoughtfully, purposefully, and often so that you can build simply, quickly, and confidently.

To hit the ground running, please read Marvin's [getting started docs](https://www.askmarvin.ai/src/getting_started/what_is_marvin/).


## Things Marvin can build in 5 minutes (seriously) 

### Scalable APIs, data pipelines, and agents

🏷️ Build bulletproof and lightning-fast classifiers

🧩 Extract structured data from unstructured text 

🧪 Generate synthetic data for your applications 

🫡 Solve complex deductive and inferential tasks at scale

🔎 Scrape web data without custom scrapers


### Chatbots with access to tools, data, and the web
😍 Customize ChatGPT with system prompts and tools

🎓 Extract relevant insights from your data

🧑‍💻 Add a junior developer to your team

🗣️ Quickly add NLP to your app

### Coming soon...
📱 AI applications with persistent state

🕵️ Autonomous agents with high-level planning

💬 Text-to-application: generate stateful applications by describing them


## Core AI Components

Marvin's high-level abstractions are familiar Python interfaces that make it easy to leverage AI in your application. These interfaces aim to be simple and self-documenting, adding a touch of AI magic to everyday objects.

### AI Models

Marvin's most basic component is the AI Model, a drop-in replacement for Pydantic's `BaseModel`. AI Models can be instantiated from any string, making them ideal for structuring data, entity extraction, and synthetic data generation. 

You can learn more about AI models [here](https://www.askmarvin.ai/src/docs/components/ai_model/).

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

### AI Functions

AI Functions look like regular functions, but have no source code. Instead, an AI uses their description and inputs to generate their outputs, making them ideal for NLP applications like sentiment analysis. 

You can learn more about AI Functions [here](https://www.askmarvin.ai/src/docs/components/ai_function/).


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

### AI Choice

AI Choice lets you build a multi-label classifier with no code and no training data. It enumerates your options, and use logit_bias to force an LLM to deductively choose the index of the best option given your provided input. It then returns the choice associated to that index. It's bulletproof, cost-effective, and lets you build classifiers as quickly as you can write your classes.

You can learn more about AI Choice [here](https://www.askmarvin.ai/src/docs/components/ai_choice/).

```python
from marvin import ai_choice
from enum import Enum


@ai_choice
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


## Installation

Marvin can be installed with pip:

```bash
pip install marvin
```

For more information please see the [installation docs](https://www.askmarvin.ai/src/getting_started/installation/).

## Documentation
Marvin's docs are available at [askmarvin.ai](https://www.askmarvin.ai), including concepts, tutorials, and an API reference.

## Community
The heart of our community beats in our Discord server. It's a space where you can ask questions, share ideas, or just chat with like-minded developers. Don't be shy, join us on [Discord](https://discord.gg/Kgw4HpcuYG) or [Twitter](https://twitter.com/AskMarvinAI)!
