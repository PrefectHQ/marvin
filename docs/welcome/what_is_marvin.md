# What is Marvin?

Marvin is a simple library that lets you use Large Language Models by writing code, not prompts. It's open source,
free to use, used by thousands of engineers, and built with love by the engineering team at Prefect. 

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

Marvin is built for incremental option. You can use it purely as a serialization library and bring your open Large Language Model,
or fully use its engine to work with OpenAI and other providers. 

!!! Example "What Marvin feels like: a few use cases."

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
            """Generates a list of {{n}} {{color}} fruits"""

        list_fruits(3) # "['Apple', 'Cherry', 'Strawberry']"
        ```
        Notice `list_fruits` has no code. Marvin's components turn your function into a prompt, ask AI for its most likely output, and
        parses its response.
    
    === "Generating Synthetic Data"

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

Marvin is a lightweight AI engineering framework for building natural language interfaces that are reliable, scalable, and easy to trust.

Sometimes the most challenging part of working with generative AI is remembering that it's not magic; it's software. It's new, it's nondeterministic, and it's incredibly powerful - but still software.

Marvin's goal is to bring the best practices for building dependable, observable software to generative AI. As the team behind [Prefect](https://github.com/prefecthq/prefect), which does something very similar for data engineers, we've poured years of open-source developer tool experience and lessons into Marvin's design.

## Core Components

🧩 [**AI Models**](/components/ai_model) for structuring text into type-safe schemas

🏷️ [**AI Classifiers**](/components/ai_classifier) for bulletproof classification and routing

🪄 [**AI Functions**](/components/ai_function) for complex business logic and transformations

🤝 [**AI Applications**](/components/ai_application) for interactive use and persistent state

## Ambient AI

With Marvin, we’re taking the first steps on a journey to deliver [Ambient AI](https://twitter.com/DrJimFan/status/1657782710344249344): omnipresent but unobtrusive autonomous routines that act as persistent translators for noisy, real-world data. Ambient AI makes unstructured data universally accessible to traditional software, allowing the entire software stack to embrace AI technology without interrupting the development workflow. Marvin brings simplicity and stability to AI engineering through abstractions that are reliable and easy to trust.

Interested? [Join our community](../../community)!
