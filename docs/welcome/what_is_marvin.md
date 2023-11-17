# What is Marvin?

Marvin is a simple library that lets you use Large Language Models by writing code, not prompts. It's open source,
free to use, and built with love by the engineering team at Prefect. 

??? Question "Explain Like I'm Five"
    === "I'm not technical"

        Marvin lets engineers who know Python use Generative AI without needing to write prompts.

        It turns out that ChatGPT and other Large Language Models are good at performing boring but incredibly valuable
        business-critical tasks beyond being a chatbot: you can use them to classify emails as spam, extract key figures
        from a report, etc. When you use something like ChatGPT you spend a lot of time crafting the right prompt or
        context to get it to write your email, plan your date night, etc.
        
        If you want your software to use ChatGPT, you need to let it turn its objective into English. Marvin handles this
        'translation' for you, so you get to just write code like you normally would. Engineers like using Marvin because it
        lets them write software like they're used to.
        
        Simply put, it lets you use Generative AI without feeling like you have to learn a framework.

    === "I'm technical"

        Marvin is a simple and elegant library to make working with Large Language Models easy, reliable, and scalable. Thousands of developers rely on Marvin in production to
    
        - Extract structured data from unstructured text, webpages, and documents
        - Classify or score text quickly and robustly
        - Create workflow automations or automate business logic in simple English

        If you know Python, you already know Marvin.



!!! Info "What is Marvin?"
    === "I write code"

        Marvin is a simple and elegant library that makes working with Large Language Models providers like OpenAI easy, reliable, and transparent. Thousands of engineers use Marvin in production to
    
        - Extract structured data from unstructured text, webpages, and documents
        - Classify or score text quickly and robustly
        - Create workflow automations or automate business logic in simple English

        If you know Python, you already know Marvin.

    === "I don't write code"

        Marvin is a simple and elegant library to make working with Large Language Models easy, reliable, and scalable. Thousands of developers rely on Marvin in production to
    
        - Extract structured data from unstructured text, webpages, and documents
        - Classify or score text quickly and robustly
        - Create workflow automations or automate business logic in simple English

        If you know Python, you already know Marvin.

!!! Example "Here's what using Marvin looks like."

    Marvin exposes a number of high level components to simplify working with AI. Below we use AI to evaluate a Python function. 

    ```python
    from marvin import ai_fn

    def list_fruits(n: int, color: str = 'red') -> list[str]:
        """Generates a list of {{n}} {{color}} fruits"""
        return ai_fn(list_fruits)(n)

    list_fruits(3) # "['Apple', 'Cherry', 'Strawberry']"
    ```
    Notice `list_fruits` has no code. Marvin's components turn your function into a prompt, ask AI for its most likely output, and
    parses its response. Of course, every part of Marvin is full customizable. 

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
