from marvin import AIApplication


def get_foo():
    """A function that returns the value of foo."""
    return 42


worker = AIApplication(
    name="worker",
    description="A simple worker application.",
    plan_enabled=False,
    state_enabled=False,
    tools=[get_foo],
)

router = AIApplication(
    name="router",
    description="routes user requests to the appropriate worker",
    plan_enabled=False,
    state_enabled=False,
    tools=[worker],
)

message = router("what is the value of foo?")

assert "42" in message.content, "The answer should be 42."
