import inspect

CAPTION_PROMPT = inspect.cleandoc(
    """
    Generate a descriptive caption for the following image, and pay attention to any
    additional instructions. Do not respond directly to the user ("you"), as
    your response will become the input for other text processing functions.

    {% if instructions -%}
    ## Instructions
    
    {{ instructions }}
    {% endif %}
    """
)
