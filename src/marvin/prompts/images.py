import inspect

IMAGE_PROMPT = inspect.cleandoc(
    """
    {{_doc | default("", true)}}
    {{_return_value | default("", true)}}
    """
)
