# What is Marvin?

Marvin is a Python library that lets you use Large Language Models by writing code, not prompts. It's open source,
free to use, rigorously type-hinted, used by thousands of engineers, and built by the engineering team at [Prefect](https://prefect.io).


??? Question "Explain Like I'm Five"
    === "I'm technical"

        Marvin lets your software speak English and ask questions to LLMs.

        It introspects the types and docstrings of your functions and data models, and lets you cast them
        to prompts automatically to pass to a Large Language Model. This lets you write code as you normally would
        instead of writing prompts, and we handle the translation back and forth for you. 

        This lets you focus on what you've always focused on: writing clean, versioned, reusable *code* and *data models*, 
        and not scrutinizing whether you begged your LLM hard enough to output JSON. 

        Extracting, generating, cleaning, or classifying data is as simple as writing a function or a data model.

    === "I'm not technical"

        Marvin lets engineers who know Python use Large Language Models without needing to write prompts.

        It turns out that ChatGPT and other Large Language Models are good at performing boring but incredibly valuable
        business-critical tasks beyond being a chatbot: you can use them to classify emails as spam, extract key figures
        from a report - exactly however you want for your scenario. When you use something like ChatGPT you spend a lot of time crafting the right prompt or
        context to get it to write your email, plan your date night, etc.
        
        If you want your software to use ChatGPT, you need to let it turn its objective into English. Marvin handles this
        'translation' for you, so you get to just write code like you normally would. Engineers like using Marvin because it
        lets them write software like they're used to.
        
        Simply put, it lets you use Generative AI without feeling like you have to learn a framework.


Marvin is lightweight and is built for incremental adoption. You can use it purely as a serialization library and bring your own stack,
or fully use its engine to work with OpenAI and other providers. 

!!! Example "What Marvin feels like."

    === "Structured Data Extraction"
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
        Notice there's no code written, just the expected types. Marvin's components turn your function into a prompt, uses AI to get its most likely output, and parses its response.
    
    === "Text Classification"
    
        Marvin exposes a number of high level components to simplify working with AI. 

        ```python
        from marvin import ai_classifier
        from typing import Literal

        @ai_classifier
        def customer_intent(text: str) -> Literal['Store Hours', 'Pharmacy', 'Returns']:
            """Classifies incoming customer intent"""

        customer_intent("I need to pick up my prescription") # "Pharmacy"

        ```
        Notice `customer_intent` has no code. Marvin's components turn your function into a prompt, ask AI for its most likely output, and
        parses its response.
    
    === "Business Logic"

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
For years we've built open source software used by tens of thousands of data and machine learning engineers daily. Marvin brings those best practices for building dependable, observable software to generative AI. 

## What models do we support?

Marvin supports any model so long as it adheres to the OpenAI spec. It's the easiest way to use Function Calling and Tool use. We run (and foot the bill for!) a public evaluation test suite to ensure that our library does what we say it does. If you're a community member who wants to build an maintain an integration with another provider, get in touch. 

Note that Marvin can be used as a serialization library, so you can bring your own Large Language Models and exclusively use Marvin to generate prompts from your code.

## Why are we building Marvin?

At Prefect we support thousands of engineers in workflow orchestration, from small startups to huge enterprise. In late 2022 we
started working with our community to adopt AI into their workflows and found there wasn't a sane option for teams looking
to build simple, quickly, and durable with Generative AI. 

## Why Marvin over alternatives?

Marvin's built and maintained by the team at Prefect. We work with thousands of engineers daily and work backwards from their 
experiences to build reliable, intuitive and pleasant interfaces to otherwise hard things. 

There's a whole fleet of frameworks to work with Large Language Models, but we're not smart enough to understand them. We
try to fight abstractions wherever we can so that users can easily understand and customize what's going on. 

