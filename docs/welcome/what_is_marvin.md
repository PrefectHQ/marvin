# Hello, Marvin!

```python
from marvin import ai_fn

@ai_fn
def quote_marvin(topic: str) -> str:
    """Quote Marvin the robot from Hitchhiker's Guide on a topic"""

quote_marvin(topic="humans") # "I've seen it. It's rubbish."
```

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
