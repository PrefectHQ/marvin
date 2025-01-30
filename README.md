![Marvin Banner](docs/assets/img/quotes/it_hates_me.png)

# Marvin

Marvin is a Python framework for building agentic AI workflows. 

Marvin provides a structured, developer-focused framework for defining workflows and delegating work to LLMs, without sacrificing control or transparency:

- Create discrete, observable **tasks** that describe your objectives.
- Assign one or more specialized AI **agents** to each task.
- Combine tasks into a **thread** to orchestrate more complex behaviors.


> [!WARNING] CONSTRUCTION ZONE
> 🚧🚨 Marvin 3.0 is currently under very active development. The API may undergo breaking changes, and documentation is still being updated. Please use it with caution. You may prefer [Marvin 2.0](https://askmarvin.ai) or [ControlFlow](https://controlflow.ai) for now.


## Example

The simplest Marvin workflow has one task, a default agent, and automatic thread management:

```python
import marvin

poem = cf.run("Write a short poem about artificial intelligence")

print(poem)
```
<details>
<summary>View the <code>poem</code></summary>
```
In circuits and code, a mind does bloom,
With algorithms weaving through the gloom.
A spark of thought in silicon's embrace,
Artificial intelligence finds its place.
```
</details>

## Why Marvin?

We believe working with AI should spark joy (and maybe a few "wow" moments):

- 🧩 **Task-Centric Architecture**: Break complex AI workflows into manageable, observable steps.
- 🤖 **Specialized Agents**: Deploy task-specific AI agents for efficient problem-solving.
- 🔒 **Type-Safe Results**: Bridge the gap between AI and traditional software with type-safe, validated outputs
- 🎛️ **Flexible Control**: Continuously tune the balance of control and autonomy in your workflows.
- 🕹️ **Multi-Agent Orchestration**: Coordinate multiple AI agents within a single workflow or task.
- 🧵 **Thread management**: Manage the agentic loop by composing tasks into customizable threads.
- 🔗 **Ecosystem Integration**: Seamlessly work with your existing code, tools, and the broader AI ecosystem.
- 🚀 **Developer Speed:** Start simple, scale up, sleep well


## Keep it Simple

Marvin includes high-level functions for the most common tasks, like summarizing text, classifying data, extracting structured information, and more.

- 📖 **Summarize**: Get a quick summary of a text
- 🏷️ **Classify**: Categorize data into predefined classes
- 🔍 **Extract**: Extract structured information from a text
- 🪄 **Cast**: Transform data into a different type
- ✨ **Generate**: Create structured data from a description
- 💬 **Say**: Converse with an LLM
- 🦾 **`@fn`**: Write custom AI functions without source code

All Marvin functions have thread management built-in, meaning they can be composed into chains of tasks that share context and history.

## Installation

Install `marvin`:

```bash
# with pip
pip install marvin

# with uv
uv add marvin
```

Configure your LLM provider (Marvin uses OpenAI by default but natively supports [all Pydantic AI models](https://ai.pydantic.dev/models/)):

```bash
export OPENAI_API_KEY=your-api-key
```

## Upgrading to Marvin 3.0

Marvin 3.0 combines the DX of Marvin 2.0 with the powerful agentic engine of [ControlFlow](https://controlflow.ai). Both Marvin and ControlFlow users will find a familiar interface, but there are some key changes to be aware of, in particular for ControlFlow users:

### Key Notes
- **Top-Level API**: Marvin 3.0's top-level API is largely unchanged for both Marvin and ControlFlow users. 
  - Marvin users will find the familiar `marvin.fn`, `marvin.classify`, `marvin.extract`, and more.
  - ControlFlow users will use `marvin.Task`, `marvin.Agent`, `marvin.run`, `marvin.Memory` instead of their ControlFlow equivalents.
- **Pydantic AI**: Marvin 3.0 uses Pydantic AI for LLM interactions, and supports the full range of LLM providers that Pydantic AI supports. ControlFlow previously used Langchain, and Marvin 2.0 was only compatible with OpenAI's models.
- **Flow → Thread**: ControlFlow's `Flow` concept has been renamed to `Thread`. It works similarly, as a context manager. The `@flow` decorator has been removed:
  ```python
  import marvin
  
  with marvin.Thread(id="optional-id-for-recovery"):
      marvin.run("do something")
      marvin.run("do another thing")
  ```
- **Database Changes**: Thread/message history is now stored in SQLite. During development:
  - Set `MARVIN_DATABASE_URL=":memory:"` for an in-memory database
  - No database migrations are currently available; expect to reset data during updates

### New Features
- **Swarms**: Use `marvin.Swarm` for OpenAI-style agent swarms:
  ```python
  import marvin

  swarm = marvin.Swarm(
      [
          marvin.Agent('Agent A'), 
          marvin.Agent('Agent B'), 
          marvin.Agent('Agent C'),
      ]
  )

  swarm.run('Everybody say hi!')
  ```
- **Teams**: A `Team` lets you control how multiple agents (or even nested teams!) work together and delegate to each other. A `Swarm` is actually a type of team in which all agents are allowed to delegate to each other at any time.
- **Marvin Functions**: Marvin's user-friendly functions have been rewritten to use the ControlFlow engine, which means they can be seamlessly integrated into your workflows. A few new functions have been added, including `summarize` and `say`.

### Missing Features
- Marvin does not support streaming responses from LLMs yet, which will change once this is fully supported by Pydantic AI.


## Workflow Example

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
        "Ask the user for a topic to write about.",
        cli=True
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