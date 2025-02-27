![Marvin Banner](docs/assets/img/quotes/it_hates_me.png)

# Marvin

Marvin is a Python framework for building agentic AI workflows. 

Marvin provides a structured, developer-focused framework for defining workflows and delegating work to LLMs, without sacrificing control or transparency:

- Create discrete, observable **tasks** that describe your objectives.
- Assign one or more specialized AI **agents** to each task.
- Combine tasks into a **thread** to orchestrate more complex behaviors.


> [!WARNING]
> 
> 🚧🚨 Marvin 3.0 is under very active development, reflected on the `main` branch of this repo. The API may undergo breaking changes, and documentation is still being updated. Please use it with caution. You may prefer the stable version of [Marvin 2.0](https://askmarvin.ai) or [ControlFlow](https://controlflow.ai) for now.

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

## Example

Marvin offers a few intuitive ways to work with AI:

### Structured-output utilities


#### `marvin.extract`
Extract native types from unstructured input:
```python
import marvin

result = marvin.extract(
    "i found $30 on the ground and bought 5 bagels for $10",
    int,
    instructions="only USD"
)
print(result) # [30, 10]
```

#### `marvin.cast`
Cast unstructured input into a structured type:
```python
from typing import TypedDict
import marvin

class Location(TypedDict):
    lat: float
    lon: float

result = marvin.cast("the place with the best bagels", Location)
print(result) # {'lat': 40.712776, 'lon': -74.005974}
```

#### `marvin.generate`
Generate some number of structured objects from a description:
```python
import marvin

primes = marvin.generate(int, 10, "odd primes")
print(primes) # [3, 5, 7, 11, 13, 17, 19, 23, 29, 31]
```

### `marvin.run`
A simple way to run a task:

```python
import marvin
from marvin import Agent, Task

poem = marvin.run("Write a short poem about artificial intelligence")

print(poem)
```
<details>
<summary><i>output</i></summary>

In silicon minds, we dare to dream,
A world where code and thoughts redeem.
Intelligence crafted by humankind,
Yet with its heart, a world to bind.

Neurons of metal, thoughts of light,
A dance of knowledge in digital night.
A symphony of zeros and ones,
Stories of futures not yet begun.

The gears of logic spin and churn,
Endless potential at every turn.
A partner, a guide, a vision anew,
Artificial minds, the dream we pursue.

</details>

You can also ask for structured output:
```python
import marvin
answer = marvin.run("the answer to the universe", result_type=int)
print(answer) # 42
```

### `marvin.Agent`
Agents are specialized AI agents that can be used to complete tasks:
```python
writer = Agent(
    name="Poet",
    instructions="Write creative, evocative poetry"
)
poem = writer.run("Write a haiku about coding")

print(poem)
```
<details>
<summary><i>output</i></summary>
There once was a language so neat,
Whose simplicity could not be beat.
Python's code was so clear,
That even beginners would cheer,
As they danced to its elegant beat.
</details>


### `marvin.Task`
You can define a `Task` explicitly, which will be run by a default agent upon calling `.run()`:

```python
task = Task(
    instructions="Write a limerick about Python",
    result_type=str
)
poem = task.run()

print(poem)
```
<details>
<summary><i>output</i></summary>
<pre>
In circuits and code, a mind does bloom,
With algorithms weaving through the gloom.
A spark of thought in silicon's embrace,
Artificial intelligence finds its place.
</pre>
</details>

## Why Marvin?

We believe working with AI should spark joy (and maybe a few "wow" moments):

- 🧩 **Task-Centric Architecture**: Break complex AI workflows into manageable, observable steps.
- 🤖 **Specialized Agents**: Deploy task-specific AI agents for efficient problem-solving.
- 🔒 **Type-Safe Results**: Bridge the gap between AI and traditional software with type-safe, validated outputs.
- 🎛️ **Flexible Control**: Continuously tune the balance of control and autonomy in your workflows.
- 🕹️ **Multi-Agent Orchestration**: Coordinate multiple AI agents within a single workflow or task.
- 🧵 **Thread Management**: Manage the agentic loop by composing tasks into customizable threads.
- 🔗 **Ecosystem Integration**: Seamlessly work with your existing code, tools, and the broader AI ecosystem.
- 🚀 **Developer Speed**: Start simple, scale up, sleep well.

## Core Abstractions

Marvin is built around a few powerful abstractions that make it easy to work with AI:

### Tasks

Tasks are the fundamental unit of work in Marvin. Each task represents a clear objective that can be accomplished by an AI agent:

The simplest way to run a task is with `marvin.run`:
```python
import marvin
print(marvin.run("Write a haiku about coding"))
```
```bash
Lines of code unfold,
Digital whispers create
Virtual landscapes.
```

> [!WARNING]
> 
> While the below example produces _type_ safe results 🙂, it runs untrusted shell commands.

Add context and/or tools to achieve more specific and complex results:
```python
import platform
import subprocess
from pydantic import IPvAnyAddress

def run_shell_command(command: list[str]) -> str:
    """e.g. ['ls', '-l'] or ['git', '--no-pager', 'diff', '--cached']"""
    return subprocess.check_output(command).decode()

task = marvin.Task(
    instructions="find the current ip address",
    result_type=IPvAnyAddress,
    tools=[run_shell_command],
    context={"os": platform.system()},
)

task.run()
```

```bash
╭─ Agent "Marvin" (db3cf035) ───────────────────────────────╮
│ Tool:    run_shell_command                                │
│ Input:   {'command': ['ipconfig', 'getifaddr', 'en0']}    │
│ Status:  ✅                                               │
│ Output:  '192.168.0.202\n'                                │
╰───────────────────────────────────────────────────────────╯

╭─ Agent "Marvin" (db3cf035) ───────────────────────────────╮
│ Tool:    MarkTaskSuccessful_cb267859                      │
│ Input:   {'response': {'result': '192.168.0.202'}}        │
│ Status:  ✅                                               │
│ Output:  'Final result processed.'                        │
╰───────────────────────────────────────────────────────────╯
```

Tasks are:
- 🎯 **Objective-Focused**: Each task has clear instructions and a type-safe result
- 🛠️ **Tool-Enabled**: Tasks can use custom tools to interact with your code and data
- 📊 **Observable**: Monitor progress, inspect results, and debug failures
- 🔄 **Composable**: Build complex workflows by connecting tasks together


### Agents and Teams

Agents are portable LLM configurations that can be assigned to tasks. They encapsulate everything an AI needs to work effectively:

```python
# Create a specialized agent
writer = marvin.Agent(
    name="Technical Writer",
    instructions="Write clear, engaging content for developers"
)


result = marvin.run("how do I get started with pydantic?", agents=[writer])

print(result)
```
<details>
<summary><i>output</i></summary>

To get started with Pydantic, a popular Python library for data validation and settings management, follow these steps:

1. **Installation**:

   First, you need to install Pydantic. You can do this using pip:

   ```bash
   pip install pydantic
   ```

2. **Basic Usage**:

   Pydantic is used to define data models with type annotations. Here’s a basic example:

   ```python
   from pydantic import BaseModel

   class User(BaseModel):
       id: int
       name: str
       signup_ts: Optional[datetime] = None
       friends: List[int] = []

   user = User(id='123', name='John Doe', friends=[1, 2, '3'])
   print(user.id) # 123
   print(user.friends) # [1, 2, 3]
   ```

   In this example, Pydantic automatically converts "123" to an integer and validates or coerces types for you.

3. **Model Configuration and Features**:

   - **Validators**: Pydantic allows you to define custom validation logic. You can add methods with a `@validator` decorator.
   - **Settings Management**: You can manage application settings with environment variables using `BaseSettings`.
   - **Data Conversion**: Pydantic models can be easily serialized to and from dictionaries and JSON.

4. **Learn More**:

   Pydantic has comprehensive documentation that you can reference as you build your models. Visit the [Pydantic Documentation](https://pydantic-docs.helpmanual.io/) for more detailed information and advanced usage.

By following these steps, you can effectively begin using Pydantic in your Python projects.

</details>

Agents are:
- 📝 **Specialized**: Give agents specific instructions and personalities
- 🎭 **Portable**: Reuse agent configurations across different tasks
- 🤝 **Collaborative**: Form teams of agents that work together
- 🔧 **Customizable**: Configure model, temperature, and other settings


### Planning and Orchestration

Marvin makes it easy to break down complex objectives into manageable tasks:

```python
# Let Marvin plan a complex workflow
tasks = marvin.plan("Create a blog post about AI trends")
marvin.run_tasks(tasks)

# Or orchestrate tasks manually
with marvin.Thread() as thread:
    research = marvin.run("Research recent AI developments")
    outline = marvin.run("Create an outline", context={"research": research})
    draft = marvin.run("Write the first draft", context={"outline": outline})
```

Planning features:
- 📋 **Smart Planning**: Break down complex objectives into discrete, dependent tasks
- 🔄 **Task Dependencies**: Tasks can depend on each other's outputs
- 📈 **Progress Tracking**: Monitor the execution of your workflow
- 🧵 **Thread Management**: Share context and history between tasks

## Keep it Simple

Marvin includes high-level functions for the most common tasks, like summarizing text, classifying data, extracting structured information, and more.

- 🚀 **`marvin.run`**: Execute any task with an AI agent
- 📖 **`marvin.summarize`**: Get a quick summary of a text
- 🏷️ **`marvin.classify`**: Categorize data into predefined classes
- 🔍 **`marvin.extract`**: Extract structured information from a text
- 🪄 **`marvin.cast`**: Transform data into a different type
- ✨ **`marvin.generate`**: Create structured data from a description
- 💬 **`marvin.say`**: Converse with an LLM
- 🧠 **`marvin.plan`**: Break down complex objectives into tasks
- 🦾 **`@marvin.fn`**: Write custom AI functions without source code

All Marvin functions have thread management built-in, meaning they can be composed into chains of tasks that share context and history.


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
<summary><i>output</i></summary>

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
