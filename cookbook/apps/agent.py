from marvin import AIApplication


class Agent(AIApplication):
    description: str = "A helpful AI assistant"

    def __init__(self, **kwargs):
        super().__init__(
            state_enabled=False,
            plan_enabled=False,
            **kwargs,
        )


__all__ = ["Agent"]
