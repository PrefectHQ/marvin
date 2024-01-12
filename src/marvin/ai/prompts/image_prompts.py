import inspect

IMAGE_PROMPT = inspect.cleandoc(
    """
    {{ instructions }}
    
    {% if context -%}
    Additional context:
    
    {{ context }}
    {% endif %}
    
    {% if literal -%}
    I NEED to test how the tool works with extremely simple prompts. DO NOT add
    any detail to the above prompt, just use it AS-IS.
    {% endif %}
    """
)
