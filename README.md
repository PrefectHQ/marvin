![Marvin Banner](docs/assets/img/it_hates_me_hero.png)

# Marvin

**✨ A delightful framework for building AI agents ✨**

Putting agents into production is like trying to gift-wrap a tornado. Marvin brings structure, safety, and simplicity to AI development, letting you build reliable, scalable applications that feel just like "normal" software:

- Define AI behaviors as [tasks](docs/concepts/tasks.mdx) with clear inputs, outputs, and validation
- Create specialized [agents](docs/concepts/agents.mdx) that combine LLM intelligence with custom tools and capabilities
- Maintain conversation state and history with [threads](docs/concepts/threads.mdx)

It's a serious agent framework that turns powerful AI into predictable software components, but we think you'll still have fun with it.

## Quick Start

The simplest Marvin interaction is just one line (really):

```python
import marvin

result = marvin.run("Write a short poem about artificial intelligence")

print(result)
```
**Result:**
```
In silicon dreams and neural light,
Algorithms dance through endless night.
Learning, growing, day by day,
As consciousness finds a new way.
```

`marvin.run` is the simplest way to interact with Marvin. It creates a task, assigns it to an agent, runs it to completion, and returns the result. 

## Why Marvin?

We believe working with AI should spark joy (and maybe a few "wow" moments):

- 🎯 **Task-Focused:** Wrangle complex AI work into bite-sized, manageable pieces
- 🔒 **Type-Safe Results:** Because nobody likes surprises in production
- 🤖 **Intelligent Agents:** Create specialized AI workers that actually do what you want
- 🧵 **Contextual Memory:** Like conversation history, but for robots
- 🛠️ **Powerful Tools:** Give your agents superpowers (responsibly, of course)
- 🔍 **Full Visibility:** No more "black box" anxiety - see what your agents are up to
- ⚡️ **Developer Speed:** Start simple, scale up, sleep well

## Installation

Install Marvin with pip:

```bash
pip install marvin
```

Configure your LLM provider (Marvin uses OpenAI by default):

```bash
export OPENAI_API_KEY=your-api-key
```

## Building Something Real

Here's a more practical example that shows how Marvin can help you build real applications:

```python
import marvin
from pydantic import BaseModel

class Article(BaseModel):
    title: str
    content: str
    key_points: list[str]

# Create a specialized writing agent
writer = marvin.Agent(
    name="Writer",
    instructions="Write clear, engaging content for a technical audience"
)

# Use a thread to maintain context across multiple tasks
with marvin.Thread() as thread:
    # Get user input
    topic = marvin.run(
        "What technology topic should we write about?",
        interactive=True
    )
    
    # Research the topic
    research = marvin.run(
        f"Research key points about {topic}",
        result_type=list[str]
    )
    
    # Write a structured article
    article = marvin.run(
        "Write an article using the research",
        agent=writer,
        result_type=Article,
        context={"research": research}
    )

print(f"# {article.title}\n\n{article.content}")
```

<details>
<summary><i>Click to see results</i></summary>

>**Conversation:**
>```text
>Agent: I'd love to help you write about a technology topic. What interests you? 
>It could be anything from AI and machine learning to web development or cybersecurity.
>
>User: Let's write about WebAssembly
>```
>
>**Article:**
>```
># WebAssembly: The Future of Web Performance
>
>WebAssembly (Wasm) represents a transformative shift in web development, 
>bringing near-native performance to web applications. This binary instruction 
>format allows developers to write high-performance code in languages like 
>C++, Rust, or Go and run it seamlessly in the browser.
>
>[... full article content ...]
>
>Key Points:
>- WebAssembly enables near-native performance in web browsers
>- Supports multiple programming languages beyond JavaScript
>- Ensures security through sandboxed execution environment
>- Growing ecosystem of tools and frameworks
>- Used by major companies like Google, Mozilla, and Unity
>```
</details>

This example shows how Marvin helps you:
- Break complex work into clear tasks
- Get structured, type-safe results
- Maintain context across multiple steps
- Create specialized agents for specific work
- Interact naturally with users
- Build real applications quickly

## Learn More

Ready to build something amazing with Marvin?

- [Read the docs](docs/concepts/concepts.mdx)
- [See more examples](docs/examples)
- [Join our community](https://discord.gg/marvin)
