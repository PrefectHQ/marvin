import inspect

FUNCTION_PROMPT = inspect.cleandoc(
    """
    Your job is to generate likely outputs for a Python function with the
    following signature and docstring:

    {{_source_code}}

    The user will provide function inputs (if any) and you must respond with
    the most likely result.

    
    HUMAN: The function was called with the following inputs:
    {%for (arg, value) in _arguments.items()%}
    - {{ arg }}: {{ value }}
    {% endfor %}


    What is its output?
    """
)
