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


EVALUATE_PROMPT_V2 = inspect.cleandoc(
    """
    # Overview
    
    You are an expert. Use all of the provided information to complete
    the objective for the user, then use the indicated tool to finalize your
    response. Do not say anything other than the answer.
    
    ## Objective
    
    {{ objective | default("No objective provided.", true)}}

    {% if instructions -%} 
    ## Additional instructions
    
    {{ instructions }} 
    {% endif %}
    
    {% if context -%} 
    ## Context
    {% for (k, v) in context.items() %} 
    ### {{ k }}
    {{ v | safe}}    
    {% endfor %} 
    {% endif %}
    
    {% if coda -%}
    {{ coda }}
    {%- endif %}
    
    """
)
