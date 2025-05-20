# Marvin Integrations

This directory contains adapters and utilities to integrate external services with Marvin.

## FastMCP Integration

The `fastmcp.py` module provides an adapter to connect Marvin agents with FastMCP servers. This integration allows Marvin agents to use tools defined on a FastMCP server.

### Design Decisions

#### 1. Lazy Loading / Optional Dependencies

The integration uses a lazy-loading pattern to avoid hard dependencies on FastMCP:

- FastMCP is imported only when needed and only if it's available
- This allows FastMCP to be an optional dependency (installed with `marvin[mcp]`)
- Users who don't need FastMCP don't need to install it

#### 2. Duck Typing for Compatibility

The adapter uses duck typing rather than strict type checking:

- Checks for required methods/attributes (`name`, `list_tools`/`_mcp_list_tools`, etc.)
- Supports both public methods and internal implementation methods
- This approach improves compatibility with different FastMCP versions and variants
- Handles cases where FastMCP may be imported from different module paths

#### 3. Stateful Import Management

The `_FastMCPImportState` class manages the import state:

- Tracks whether import has been attempted to avoid repeated import attempts
- Stores the imported FastMCP type for later reference
- Stores a reference to the conversion function
- This encapsulation simplifies state management and keeps global namespace clean

#### 4. Detection Heuristics

Detection of FastMCP servers uses multiple heuristics:

- Class name contains "FastMCP"
- Required method presence
- This "belt and suspenders" approach improves reliability when dealing with various FastMCP implementations

#### 5. Error Handling and Diagnostics

The module includes comprehensive error handling and logging:

- Provides clear error messages when FastMCP isn't installed
- Logs detailed diagnostics during initialization and method calls
- Exception handling during adapter creation for better debugging

### Potential Improvements

If you're rewriting this code, consider these potential improvements:

1. Use a proper dependency injection framework instead of global state
2. Create a more formal protocol/interface for MCPServer implementations
3. Implement a registry of adapters rather than the current if/elif approach
4. Consider moving adapter detection to registration time rather than usage time
5. Add more comprehensive unit tests for different FastMCP server types
6. Improve type safety by using Protocol classes from typing module

### Usage

When a Marvin Agent is initialized with a FastMCP server in its `mcp_servers` list:

```python
from fastmcp.server import FastMCP
import marvin

# Create a FastMCP server
server = FastMCP("My Server")

@server.tool()
def hello_world() -> str:
    return "Hello, world!"

# Use the server with a Marvin agent
agent = marvin.Agent(mcp_servers=[server])
result = agent.run("Please say hello to the world")
```

The FastMCP server is automatically detected and adapted to the MCPServer interface expected by Marvin. This happens transparently to the user, who only needs to provide the FastMCP server instance directly.