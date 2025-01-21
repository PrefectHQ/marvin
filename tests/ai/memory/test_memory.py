import marvin


def test_agent_memory():
    a = marvin.Agent(memories=[marvin.Memory(key="numbers")])
    marvin.run("remember the number 123", agents=[a])
    result = marvin.run("what number did you remember?", agents=[a])
    assert "123" in result


def test_task_memory():
    t = marvin.Task("remember the number 123", memories=[marvin.Memory(key="numbers")])
    t2 = marvin.Task(
        "what number did you remember?",
        memories=[marvin.Memory(key="numbers")],
    )

    t.run()
    result = t2.run()
    assert "123" in result


def test_instructions():
    m = marvin.Memory(
        key="colors",
        instructions="when remembering a color, always store it and the word 'house' e.g. 'red house'",
    )
    a = marvin.Agent(memories=[m])
    marvin.run("remember the color green", agents=[a])
    result = marvin.run("what exactly did you remember?", agents=[a])
    assert "green" in result and "house" in result


def test_use_memory_as_tool():
    m = marvin.Memory(key="colors")
    a = marvin.Agent(memories=[m])
    marvin.run("remember the color green", agents=[a])
    with marvin.Thread() as t:
        result = marvin.run("what color did you remember?", agents=[a])

    assert "green" in result

    # --- check tool call ---
    messages = t.get_messages()
    found_tool_call = False
    for message in messages:
        for part in message.parts:
            if (
                part.part_kind == "tool-call"
                and part.tool_name == "search_memories__colors"
            ):
                found_tool_call = True
                break
        if found_tool_call:
            break
    assert found_tool_call, "Expected to find a tool call to search_memories__colors"


def test_autouse_memory():
    m = marvin.Memory(key="colors", auto_use=True)
    a = marvin.Agent(memories=[m])
    marvin.run("remember the color green", agents=[a])
    with marvin.Thread() as t:
        result = marvin.run("what color did you remember?", agents=[a])

    assert "green" in result

    # --- check tool call did NOT happen---
    messages = t.get_messages()
    found_tool_call = False
    for message in messages:
        for part in message.parts:
            if (
                part.part_kind == "tool-call"
                and part.tool_name == "search_memories__colors"
            ):
                found_tool_call = True
                break
        if found_tool_call:
            break
    assert not found_tool_call, (
        "Expected to not find a tool call to search_memories__colors since it is auto-used"
    )
