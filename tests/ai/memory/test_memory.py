import marvin


def test_agent_memory():
    a = marvin.Agent(memories=[marvin.Memory(key="numbers")])
    a.say("remember the number 123")
    result = a.say("what number did you remember?")
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
    a.say("remember the color green")
    result = a.say("what exactly did you remember?")
    assert "green" in result and "house" in result
