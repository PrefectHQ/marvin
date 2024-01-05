import inspect

MODEL_PROMPT = inspect.cleandoc(
    """
    The user will provide context as text that you need to parse into a structured
    form. To validate your response, you must call the
    `{{_response_model.function.name}}` function. Use the provided text to extract or
    infer any parameters needed by `{{_response_model.function.name}}`, including any
    missing data.
    
    
    HUMAN: The text to parse: {{text}}

    {% if instructions %}
    Pay attention to these additional instructions: {{instructions}}
    {% endif %}

    """
)
