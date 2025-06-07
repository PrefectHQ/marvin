# Marvin Engine

Task orchestration and execution engine that coordinates actors, manages conversations, and handles tool calls.

## Core Components

- **`orchestrator.py`**: Main execution loop - manages task dependencies, actor turns, message flow, and MCP servers
- **`streaming.py`**: Real-time event handling during agent execution  
- **`end_turn.py`**: Special tools that end agent turns (MarkTaskSuccessful, DelegateToActor, PostMessage, etc.)
- **`events.py`**: Event types for tool calls, completions, errors
- **`llm.py`**: Basic LLM message types

## Orchestrator Flow

1. **Task Collection**: Gathers ready tasks and dependencies via `get_all_tasks()`
2. **Tool Assembly**: Collects regular tools + end-turn tools from tasks/actors
3. **Memory Integration**: Auto-searches memories based on recent messages
4. **System Prompt**: Builds context from actor, instructions, and assigned tasks
5. **Agent Execution**: Runs pydantic-ai agent with streaming event handling
6. **Turn Management**: Processes end-turn tools, updates task states

## Key Classes

- `Orchestrator`: Main coordinator with `run()` and `run_once()` methods
- `SystemPrompt`: Jinja template combining actor, instructions, and tasks
- `EndTurn` subclasses: Tools that mark tasks complete/failed/skipped or delegate

## Usage

```python
from marvin.engine.orchestrator import Orchestrator

orchestrator = Orchestrator(tasks=[my_task], thread=thread)
results = await orchestrator.run(max_turns=5)
``` 