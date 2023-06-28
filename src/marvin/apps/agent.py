from marvin import AIApplication


class Agent(AIApplication):
    description: str = "A helpful AI assistant"

    def __init__(
        self,
        description: str = None,
        **kwargs,
    ):
        super().__init__(
            description=description,
            app_state_enabled=False,
            ai_state_enabled=False,
            **kwargs,
        )


__all__ = ["Agent"]
