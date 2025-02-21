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


## Example

Marvin offers three intuitive ways to work with AI:

```python
import marvin
from marvin import Agent, Task

# 1. Quick one-liners with marvin.run()
poem = marvin.run("Write a short poem about artificial intelligence")

# 2. Agent-specific tasks
writer = Agent(
    name="Poet",
    instructions="Write creative, evocative poetry"
)
poem = writer.run("Write a haiku about coding")

# 3. Full task control
task = Task(
    instructions="Write a limerick about Python",
    result_type=str
)
poem = task.run()

print(poem)
```
<details>
<summary>View the <code>poem</code></summary>
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

```python
# The simplest way to run a task
result = marvin.run("Write a haiku about coding")

# Create a task with more control
task = marvin.Task(
    instructions="Write a haiku about coding",
    result_type=str,
    tools=[my_custom_tool]
)
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

# Create a team of agents that work together
team = marvin.Swarm([
    writer,
    marvin.Agent("Editor"),
    marvin.Agent("Fact Checker")
])

# Use agents with tasks
result = marvin.run(
    "Write a blog post about Python type hints",
    agents=[team]
)
```

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
- ✨ **`