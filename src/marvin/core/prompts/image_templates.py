import inspect

IMAGE_PROMPT = inspect.cleandoc(
    """
    {{ instructions }}
    
    Additional context:
    {{ context }}
    """
)
