# Marvin Tools

Minimal tool infrastructure - most tools come from agents, tasks, memories, and MCP servers.

## What's Here

- **`thread.py`**: Single function `post_message_to_agents()` for inter-agent communication
- **`interactive/cli.py`**: Interactive CLI tools for user input during agent execution

## Tool Sources

Tools are provided by:
- **Agent.get_tools()**: Agent-specific functions  
- **Task.get_tools()**: Task-related functions
- **Memory.get_tools()**: Memory search/retrieval functions
- **MCP Servers**: External tools via Model Context Protocol

## Utilities (`utilities/tools.py`)

- **`update_fn()`**: Modify function name/docstring dynamically
- **`wrap_tool_errors()`**: Convert exceptions to `ModelRetry` for pydantic-ai
- **`ResultTool`**: Dataclass for result-type tools

## Tool Error Handling

```python
# All tools get wrapped automatically
@wrap_tool_errors  
def my_tool():
    # Any exception becomes ModelRetry
    raise ValueError("Tool failed")
```

## MCP Integration

External tools via MCP servers are discovered and wrapped automatically:
- Server tools converted to pydantic-ai format
- Full async/sync support  
- Error handling via `_mcp_tool_wrapper()`

## Usage Pattern

Tools are regular Python functions - no special base classes required. Function signature + docstring = tool schema. 