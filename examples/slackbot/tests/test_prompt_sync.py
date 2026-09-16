"""Drift guards keeping the system prompt honest against the code.

The system prompt must never reference tools that don't exist (a previous
version told the agent to consult a nonexistent `verify_import_statements`
tool), and per-tool guidance lives in docstrings, so every tool on the agent
must actually have one.
"""

import re
from pathlib import Path

from slackbot._internal.templates import DEFAULT_SYSTEM_PROMPT

CORE_SOURCE = (
    Path(__file__).parent.parent / "src" / "slackbot" / "core.py"
).read_text()


def _registered_tool_names() -> set[str]:
    """Tool names on the agent: the `tools=[...]` list plus @agent.tool defs."""
    names: set[str] = set()
    tools_list = re.search(r"tools=\[(.*?)\]", CORE_SOURCE, re.S)
    assert tools_list is not None, "could not find tools=[...] in core.py"
    for line in tools_list.group(1).splitlines():
        entry = line.split("#")[0].strip().rstrip(",")
        if entry:
            names.add(entry)
    names.update(re.findall(r"@agent\.tool\s+(?:async )?def (\w+)", CORE_SOURCE))
    return names


def test_prompt_only_references_real_tools():
    registered = _registered_tool_names()
    assert registered, "no tools found on the agent"
    # scan every word, not just backticked ones — a plain-text mention of a
    # nonexistent tool is just as misleading to the model
    referenced = set(re.findall(r"\w+", DEFAULT_SYSTEM_PROMPT))
    tool_like = {
        name
        for name in referenced
        if re.fullmatch(
            r"(?:store|delete|search|read|check|create|display|explore|research|verify|get)_\w+",
            name,
        )
    }
    dangling = tool_like - registered
    assert not dangling, (
        f"system prompt references tools that don't exist on the agent: {dangling}"
    )


def test_every_registered_tool_has_a_docstring():
    import slackbot.core as core
    import slackbot.research_agent as research_agent
    import slackbot.search as search

    for name in _registered_tool_names():
        fn = None
        for module in (core, search, research_agent):
            fn = getattr(module, name, None)
            if fn is not None:
                break
        if fn is None:
            # @agent.tool functions are defined inside create_agent; check
            # source for a docstring immediately after the def instead
            pattern = rf"def {name}\(.*?\)[^:]*:\n\s+\"\"\""
            assert re.search(pattern, CORE_SOURCE, re.S), (
                f"agent tool {name} has no docstring"
            )
            continue
        doc = getattr(fn, "__doc__", None) or getattr(
            getattr(fn, "fn", None), "__doc__", None
        )
        assert doc and doc.strip(), f"tool {name} has no docstring"
