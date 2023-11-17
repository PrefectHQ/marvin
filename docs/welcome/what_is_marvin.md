# What is Marvin?

Marvin is a simple library that lets you use Large Language Models by writing code, not prompts. It's open source,
free to use, used by thousands of engineers, and built with love by the engineering team at [Prefect](https://github.com/prefecthq/prefect). 

??? Question "Explain Like I'm Five"
    === "I'm not technical"

        Marvin lets engineers who know Python use Large Language Models without needing to write prompts.

        It turns out that ChatGPT and other Large Language Models are good at performing boring but incredibly valuable
        business-critical tasks beyond being a chatbot: you can use them to classify emails as spam, extract key figures
        from a report, etc. When you use something like ChatGPT you spend a lot of time crafting the right prompt or
        context to get it to write your email, plan your date night, etc.
        
        If you want your software to use ChatGPT, you need to let it turn its objective into English. Marvin handles this
        'translation' for you, so you get to just write code like you normally would. Engineers like using Marvin because it
        lets them write software like they're used to.
        
        Simply put, it lets you use Generative AI without feeling like you have to learn a framework.

    === "I'm technical"

        Marvin lets your software speak English and ask questions to LLMs.

        It introspects the types and docstrings of your functions and data models, and lets you cast them
        to prompts automatically to pass to a Large Language Model. This lets you write code as you normally would
        instead of writing prompts, and we handle the translation back and forth for you. 

        This lets you focus on what you've always focused on: writing clean, versioned, reusable *code* and *data models*, 
        and not scrutinizing whether you begged your LLM hard enough to output JSON. 

        Extracting, generating, cleaning, or classifying data is as simple as writing a function or a data model.

Marvin is built for incremental adoption. You can use it purely as a serialization library and bring your own stack,
or fully use its engine to work with OpenAI and other providers. 

!!! Example "What Marvin feels like."

    === "Extracting structured data"
        Marvin exposes a number of high level components to simplify working with AI. 

        ```python
        from marvin.components import ai_model
        from pydantic import BaseModel

        class Location(BaseModel):
            city: str
            state: str
            latitude: float
            longitude: float

        ai_model(Location)("They say they're from the Windy City!")
        # Location(city='Chicago', state='Illinois', latitude=41.8781, longitude=-87.6298)
        ```
        Marvin's components turn your function into a prompt, ask AI for its most likely output, and parses its response.
    
    === "Building text classifiers"
    
        Marvin exposes a number of high level components to simplify working with AI. 

        ```python
        from marvin import ai_classifier
        from typing import Literal

        @ai_classifier
        def customer_intent(n: int, color: str = 'red') -> Literal['Store Hours', 'Pharmacy', 'Returns']
            """Classifies incoming customer intent"""

        customer_intent("I need to pick up my prescription") # "Pharmacy"
        ```
        Notice `customer_intent` has no code. Marvin's components turn your function into a prompt, ask AI for its most likely output, and
        parses its response.
    
    === "Generating synthetic data"

        Marvin exposes a number of high level components to simplify working with AI. 

        ```python
        from marvin import ai_fn

        @ai_fn
        def list_fruits(n: int, color: str = 'red') -> list[str]:
            """Generates a list of {{n}} {{color}} fruits"""

        list_fruits(3) # "['Apple', 'Cherry', 'Strawberry']"
        ```
        Notice `list_fruits` has no code. Marvin's components turn your function into a prompt, ask AI for its most likely output, and
        parses its response.

Marvin's goal is to bring the best practices for building dependable, observable software to generative AI. As the team behind [Prefect](https://github.com/prefecthq/prefect), which does something very similar for data engineers, we've poured years of open-source developer tool experience and lessons into Marvin's design.

## What models do we support?

Marvin officially supports OpenAI's suite of models. It's the easiest way to use OpenAI Function Calling. We run (and pay for!) a public evaluation test suite to ensure that our library does what we say it does. If you're a community member who wants to build an maintain an integration with another provider, get in touch. 

Note that Marvin can be used as a serialization library, so you can bring your own Large Language Models and exclusively use Marvin to generate prompts from your code.

## Why are we building Marvin?

At Prefect we support thousands of engineers in workflow orchestration, from small startups to huge enterprise. In late 2022 we
started working with our community to adopt AI into their workflows and found there wasn't a sane option for teams looking
to build simple, quickly, and durable with Generative AI. 

## Why Marvin over X?

There's a whole fleet of frameworks to work with Large Language Models, but we're not smart enough to understand them. We
try to fight abstractions wherever we can so that users can easily understand and customize what's going on. 

At Prefect we've worked for years to find a developer experience that engineers find inuitive and pleasant to work with. We're porting our
lessons from Prefect to working with Generative AI.  