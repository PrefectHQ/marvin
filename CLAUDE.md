# Marvin - AI Engineering Toolkit

Marvin is a lightweight AI engineering toolkit for building natural language interfaces that are reliable, scalable, and easy to trust.

## Reproductions
- use the repros folder to reproduce the results (e.g. `uv run repros/1234.py`)
- this folder is not checked into git

## Architecture & Design Philosophy

- **Aggressively minimal and elegant**: Keep implementations simple and focused
- **Functional first**: Prefer functional approaches, use classes where justified  
- **Type-safe**: Full type annotations, modern Python syntax (3.10+)
- **Private internals**: Keep implementation details "private" (e.g. `def _impl`)

## Key Components

- **Engine**: Core AI interaction layer
- **Tasks**: Structured AI task definitions and execution
- **Tools**: Extensible function calling capabilities
- **Agents**: AI agents with tool access and memory
- **Memory**: Persistent conversation and context storage
- **Handlers**: Event processing and routing
- **CLI**: Command-line interface for common operations

## Development Guidelines

### Type Hints
- Use `X | Y` instead of `Union[X, Y]`
- Use builtins like `list`, `dict` instead of `typing.List`, `typing.Dict`
- Use `T | None` instead of `Optional`

### Dependencies & Running
- Use `uv` for dependency management and script execution
- Install deps: `uv sync` or `uv sync --extra foo`
- Run scripts: `uv run some/script.py` or `uv run --with pandas script.py`
- Testing: `uv run pytest` or `uv run pytest -n3` for parallel

### Finding Things
- Use `rg` for searching, not grep
- Use `ls` and `tree` for navigation
- Check git context with `gh` and `git` commands
- Think like a hacker with good intentions - search in site-packages when needed

### Linter Philosophy
- Empirically understand by running code
- Linter tells basic truths but may be orthogonal to goals
- Don't obsess over upstream linter errors, use as clues when relevant 