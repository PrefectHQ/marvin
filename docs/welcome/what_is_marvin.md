# What is Marvin

!!! Info "What is Marvin"
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
