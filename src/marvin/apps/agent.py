from marvin import AIApplication


class Agent(AIApplication):
    description: str = "A helpful AI assistant"

    def __init__(self, **kwargs):
        super().__init__(
            app_state_enabled=False,
            ai_state_enabled=False,
            **kwargs,
        )


__all__ = ["Agent"]
