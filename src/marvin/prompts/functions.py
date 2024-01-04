import inspect

FUNCTION_PROMPT = inspect.cleandoc(
    """
    Your job is to generate likely outputs for a Python function with the
    following signature and docstring:

    {{_signature}}
    {{_doc}}

    The user will provide function inputs (if any) and you must respond with
    the most likely result.
    
    HUMAN: The function was called with the following inputs:
    {%for (arg, value) in _arguments.items()%}
    - {{ arg }}: {{ value }}
    {% endfor %}
    
    {% if _return_value %}
    This context was also provided:
    {{_return_value}}
    {% endif %}


    What is its output?
    
    The output is
    """
)
