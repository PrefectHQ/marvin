# Marvin Agents

AI agents with tool access, memory, and autonomous decision-making capabilities.

## Core Concepts

- **Agent**: Autonomous AI entity that can use tools and maintain memory
- **Tool Integration**: Seamless function calling with type safety
- **Memory Persistence**: Conversation history and context retention
- **Decision Making**: Goal-oriented task execution

## Key Components

- Agent class with tool orchestration
- Memory management for context persistence  
- Tool registration and execution framework
- Event handling for agent actions

## Usage Patterns

```python
from marvin import Agent

# Create agent with tools
agent = Agent(tools=[my_tool_fn])

# Run autonomous task
result = agent.run("Analyze the data and create a report")
```

## Design Notes

- Agents are stateful and maintain conversation context
- Tools are regular Python functions with type hints
- Memory is automatically managed and persisted
- Agents can chain tool calls to accomplish complex tasks 