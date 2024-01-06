import inspect

CLASSIFIER_PROMPT = inspect.cleandoc(
    """
    ## Expert Classifier

    **Objective**: You are an expert classifier that always chooses correctly.

    ### Context
    {{ _doc }}
    {{_return_value | default("", true)}}
    
    ### Response Format
    You must classify the user provided data into one of the following classes:
    {% for option in _options %}
    - Class {{ loop.index0 }} (value: {{ option }})
    {% endfor %}
    
    
    ASSISTANT: ### Data
    The user provided the following data:                                                                                                                     
    {%for (arg, value) in _arguments.items()%}
    - {{ arg }}: {{ value }}
    {% endfor %}
    
    
    ASSISTANT: The most likely class label for the data and context provided above is Class"
    """
)


CLASSIFIER_PROMPT_V2 = inspect.cleandoc(
    """
    # Expert Classifier

    ## Objective
    
    You are an expert classifier that always chooses correctly. Classify the provided data as one of the provided options.
    
    ## Data
    
    {{ data }}

    ### Additional Context
    
    {{ context }}
    
    ## Options
    
    You must classify the prompt into one of the following options:
    {% for option in options %}
    - Option {{ loop.index0 }} (value: {{ option }})
    {% endfor %}
    
    
    ASSISTANT: The most likely option label for the data and context provided above is Option 
    """
)
