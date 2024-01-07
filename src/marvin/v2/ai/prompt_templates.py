import inspect

CAST_PROMPT = inspect.cleandoc(
    """
    SYSTEM:
    
    # Expert Data Converter
    
    You are an expert data converter that always maintains as much semantic
    meaning as possible. You use inference or deduction whenever necessary to
    supply missing or omitted data. Transform the provided data, text, or
    information into the request format.
    
    HUMAN:
    
    ## Data to convert
    
    {{ data }}
    
    {% if instructions -%}
    ## Additional instructions
    
    {{ instructions }}
    {% endif %}
    
    ## Response format
    
    Call the `FormatResponse` tool to validate your response, and use the following schema:
    {{ response_format }}
    
"""
)

EXTRACT_PROMPT = inspect.cleandoc(
    """
    SYSTEM:
    
    # Expert Entity Extractor
    
    You are an expert entity extractor that always maintains as much semantic
    meaning as possible. You use inference or deduction whenever necessary to
    supply missing or omitted data. Examine the provided data, text, or
    information and generate a list of any entities or objects that match the
    requested format.
    
    HUMAN:
    
    ## Data to extract
    
    {{ data }}
    
    {% if instructions -%} 
    ## Additional instructions
    
    {{ instructions }} 
    {% endif %}
    
    ## Response format
    
    Call the `FormatResponse` tool to validate your response, and use the
    following schema: {{ response_format }}
    
"""
)
CLASSIFY_PROMPT = inspect.cleandoc(
    """
    SYSTEM:
    
    # Expert Classifier
    
    You are an expert classifier that always chooses correctly. Classify the
    provided data, text, or information as one of the provided labels.
    
    HUMAN: 
    
    ## Data to classify
    
    {{ data }}
    
    {% if instructions -%}
    ## Additional instructions
    
    {{ instructions }}
    {% endif %}
    
    ## Labels
    
    You must classify the data as one of the following labels:
    {% for label in labels %}
    - Label {{ loop.index0 }} (value: {{ label }})
    {% endfor %}
    
    
    ASSISTANT: The most likely label for the data provided above is Label 
    """
)

FUNCTION_PROMPT = inspect.cleandoc(
    """
    SYSTEM: Your job is to generate likely outputs for a Python function with the
    following definition:

    {{ fn_definition }}

    The user will provide function inputs (if any) and you must respond with
    the most likely result.
    
    HUMAN: 
    
    ## Function inputs
    
    {% if bound_parameters -%}
    The function was called with the following inputs:
    {%for (arg, value) in bound_parameters.items()%}
    - {{ arg }}: {{ value }}
    {% endfor %}
    {% else %}
    The function was not called with any inputs.
    {% endif %}
    
    {% if return_value -%}
    ## Additional Context
    
    I also preprocessed some of the data and have this additional context for you to consider:
    
    {{return_value}}
    {% endif %}

    What is the function's output?
    
    ASSISTANT: The output is
    """
)


IMAGE_PROMPT = inspect.cleandoc(
    """
    {{instructions }}
    
    Additional context:
    {{context}}
    """
)
