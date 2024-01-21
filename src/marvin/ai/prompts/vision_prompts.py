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

CAPTION_FOR_OBJECTIVE_PROMPT = inspect.cleandoc(
    """
    The following data and images are being used to complete an objective. The
    objective itself will be performed by a different AI that can only process
    text, so you must process these images into text in a way that will maximize
    the other AI's ability to complete the objective. You should produce the
    most succinct response that contains any information relevant to the
    objective, while still providing some context. You can take the `data` into
    account but do not need to reproduce it because it will be provided to the
    other AI as well. You must pay attention to any additional instructions. Do
    not tell the other AI exactly what to do, as it will get confused. Just
    return data that it can decide to incorporate (or even repeat) in its own
    response.
    
    
    ## Objective
    
    {{ objective }}
    
    ## Data
        
    {{ data if data else "(No additional data was provided.)"}}
    
    ## Instructions
    
    {{ instructions if instructions else "(No additional instructions were provided.)" }}
    
    ASSISTANT: The description of the image(s) and data that is most relevant to the
    objective is: 
    """
)
