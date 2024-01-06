import inspect

IMAGE_PROMPT = inspect.cleandoc(
    """
    {{_doc | default("", true)}}
    {{_return_value | default("", true)}}
    """
)

IMAGE_PROMPT_V2 = inspect.cleandoc(
    """
    {{instructions }}
    
    Additional context:
    {{context}}
    """
)
