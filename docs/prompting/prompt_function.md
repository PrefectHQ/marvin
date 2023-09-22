Marvin puts the engineering in prompt engineering. We expose a low-level `prompt_fn` decorator that lets you write prompts as *functions*. This lets you build fully type-hinted prompts that other engineers can introspect, version, and test.

This is the easiest way to use Azure / OpenAI's function calling API.

## Basic Use

### Type Hinting

!!! Example 

    Marvin translates your Python code into English. We'll simply write a Python function, 
    tell it that we expect an integer input `n` input and that it'll 
    output `list[str]`, or a list of strings. With Marvin, we'll use `prompt_fn` and decorate this function. 
    When we do, this function can be cast to a payload that can be send to an LLM.
    
    ```python

    from marvin.prompts import prompt_fn

    @prompt_fn
    def list_fruits(n: int, color: str = 'red') -> list[str]:
        '''Generates a list of {{n}} {{color}} fruits'''

    list_fruits(3, color = 'blue').serialize()

    ```
    This function can now be run and serialized to an Azure / OpenAI Function Calling payload.

    ??? success "Click to see results: ```list_fruits(3, color = 'blue').serialize()```"
        ```python
            {
            "messages": [
                {
                "role": "system",
                "content": "Generates a list of 3 blue fruits"
                }
            ],
            "functions": [
                {
                "parameters": {
                    "type": "object",
                    "properties": {
                    "output": {
                        "title": "Output",
                        "type": "array",
                        "items": {
                        "type": "string"
                        }
                    }
                    },
                    "required": [
                    "output"
                    ]
                },
                "name": "Output",
                "description": ""
                }
            ],
            "function_call": {
                "name": "Output"
            }
            }

        ```

## Advanced Use

### Use with Pydantic

!!! Example 

    Marvin supports type-hinting with Pydantic, so your return annotation can be a more complex
    data-model.
    
    ```python

    from marvin.prompts import prompt_fn
    from pydantic import BaseModel

    class Fruit(BaseModel):
        color: str

    @prompt_fn
    def list_fruits(n: int, color: str = 'red') -> list[Fruit]:
        '''Generates a list of {{n}} {{color}} fruits'''

    list_fruits(3, color = 'blue').serialize()

    ```
    This function can now be run and serialized to an Azure / OpenAI Function Calling payload.

    ??? success "Click to see results: ```list_fruits(3, color = 'blue').serialize()```"
        ```python
            {
            "messages": [
                {
                "role": "system",
                "content": "Generates a list of 3 blue fruits"
                }
            ],
            "functions": [
                {
                "parameters": {
                    "type": "object",
                    "properties": {
                    "output": {
                        "title": "Output",
                        "type": "array",
                        "items": {
                        "$ref": "#/definitions/Fruit"
                        }
                    }
                    },
                    "required": [
                    "output"
                    ],
                    "definitions": {
                    "Fruit": {
                        "title": "Fruit",
                        "type": "object",
                        "properties": {
                        "color": {
                            "title": "Color",
                            "type": "string"
                        }
                        },
                        "required": [
                        "color"
                        ]
                    }
                    }
                },
                "name": "FruitList",
                "description": ""
                }
            ],
            "function_call": {
                "name": "FruitList"
            }
            }

        ```



### Full Customization 

!!! Example 

    Marvin supports full customization of every element of your prompts. You can customize the 
    name, description, and field_names of your `response_model`. 

    Say we want to change the task to generate in Swedish.
    
    ```python

    from marvin.prompts import prompt_fn
    from pydantic import BaseModel

    class Fruit(BaseModel):
        color: str

    @prompt_fn(
        response_model_name = 'Fruktlista', 
        response_model_description = 'A list of fruits in Swedish',
        response_model_field_name = 'Frukt'
    )
    def list_fruits(n: int, color: str = 'red') -> list[Fruit]:
        '''Generates a list of {{n}} {{color}} fruits'''
        
    list_fruits(3, color = 'blue').serialize()

    ```
    This function can now be run and serialized to an Azure / OpenAI Function Calling payload.

    ??? success "Click to see results: ```list_fruits(3, color = 'blue').serialize()```"
        ```python
            {
            "messages": [
                {
                "role": "system",
                "content": "Generates a list of 3 blue fruits"
                }
            ],
            "functions": [
                {
                "parameters": {
                    "type": "object",
                    "properties": {
                    "Frukt": {
                        "title": "Frukt",
                        "type": "array",
                        "items": {
                        "$ref": "#/definitions/Fruit"
                        }
                    }
                    },
                    "required": [
                    "Frukt"
                    ],
                    "definitions": {
                    "Fruit": {
                        "title": "Fruit",
                        "type": "object",
                        "properties": {
                        "color": {
                            "title": "Color",
                            "type": "string"
                        }
                        },
                        "required": [
                        "color"
                        ]
                    }
                    }
                },
                "name": "Fruktlista",
                "description": "A list of fruits in Swedish"
                }
            ],
            "function_call": {
                "name": "Fruktlista"
            }
            }
        ```



### Referencing Globals

!!! Example 

    Marvin passes the name of your response model to the prompt for you to reference
    as a convenience.

    Say we want to change the task to generate in Swedish.
    
    ```python
    from marvin.prompts import prompt_fn
    from pydantic import BaseModel

    class Fruit(BaseModel):
        color: str

    @prompt_fn(response_model_name = 'Fruits')
    def list_fruits(n: int, color: str = 'red') -> list[Fruit]:
        '''Generates a list of {{n}} {{color}} {{response_model.__name__.lower()}}'''
        
    list_fruits(3, color = 'blue').serialize()

    ```
    This function can now be run and serialized to an Azure / OpenAI Function Calling payload.

    ??? success "Click to see results: ```list_fruits(3, color = 'blue').serialize()```"
        ```python
            {
                "messages": [
                    {
                    "role": "system",
                    "content": "Generates a list of 3 blue fruits"
                    }
                ],
                "functions": [
                    {
                    "parameters": {
                        "type": "object",
                        "properties": {
                        "output": {
                            "title": "Output",
                            "type": "array",
                            "items": {
                            "$ref": "#/definitions/Fruit"
                            }
                        }
                        },
                        "required": [
                        "output"
                        ],
                        "definitions": {
                        "Fruit": {
                            "title": "Fruit",
                            "type": "object",
                            "properties": {
                            "color": {
                                "title": "Color",
                                "type": "string"
                            }
                            },
                            "required": [
                            "color"
                            ]
                        }
                        }
                    },
                    "name": "Fruits",
                    "description": ""
                    }
                ],
                "function_call": {
                    "name": "Fruits"
                }
                }
        ```

### Contexts

!!! Example 

    Marvin supports full passing context dictionaries to your prompt's rendering environment.

    Say we want to list 'seasonal' fruits. We'll pass the datetime.
    
    ```python
    from marvin.prompts import prompt_fn
    from datetime import date

    @prompt_fn(ctx = {'today': date.today()})
    def list_fruits(n: int, color: str = 'red') -> list[str]:
        ''' 
        Generates a list of {{n}} {{color}} fruits in season.
            - The date is {{today}}
        '''
    ```

    This function can now be run and serialized to an Azure / OpenAI Function Calling payload.

    ??? success "Click to see results: ```list_fruits(3, color = 'blue').serialize()```"
        ```python
            {
                "messages": [
                    {
                    "role": "system",
                    "content": "Generates a list of 3 blue fruits in season.\n- The date is 2023-09-22"
                    }
                ],
                "functions": [
                    {
                    "parameters": {
                        "type": "object",
                        "properties": {
                        "output": {
                            "title": "Output",
                            "type": "array",
                            "items": {
                            "type": "string"
                            }
                        }
                        },
                        "required": [
                        "output"
                        ]
                    },
                    "name": "Output",
                    "description": ""
                    }
                ],
                "function_call": {
                    "name": "Output"
                }
                }
        ```

### Multi-Turn Prompts

!!! Example 

    Marvin supports multi-turn conversations. If no role is specified, the whole block is assumed
    to be a system prompt. To override this default behavior, simply break into Human, System, Assistant
    turns. 
    
    ```python
    from marvin.prompts import prompt_fn
    from datetime import date

    @prompt_fn(ctx = {'today': date.today()})
    def list_fruits(n: int, color: str = 'red') -> list[str]:
        ''' 
        System: You generate a list of {{ n }} fruits in season.
            - The date is {{ today }}

        User: I want {{ color }} fruits only.
        '''

    ```

    This function can now be run and serialized to an Azure / OpenAI Function Calling payload.

    ??? success "Click to see results: ```list_fruits(3, color = 'blue').serialize()```"
        ```python
            {
                "messages": [
                    {
                    "role": "system",
                    "content": "You generate a list of 3 fruits in season.\n- The date is 2023-09-22"
                    },
                    {
                    "role": "user",
                    "content": "I want blue fruits."
                    }
                ],
                "functions": [
                    {
                    "parameters": {
                        "type": "object",
                        "properties": {
                        "output": {
                            "title": "Output",
                            "type": "array",
                            "items": {
                            "type": "string"
                            }
                        }
                        },
                        "required": [
                        "output"
                        ]
                    },
                    "name": "Output",
                    "description": ""
                    }
                ],
                "function_call": {
                    "name": "Output"
                }
                }
        ```

## Use Cases

### Classification

!!! Example 

    Marvin supports multi-turn conversations. If no role is specified, the whole block is assumed
    to be a system prompt. To override this default behavior, simply break into Human, System, Assistant
    turns. 
    
    ```python
    from marvin.prompts import prompt_fn
    from typing import Optional
    from enum import Enum

    class Food(Enum):
        '''
            Food classes
        '''
        FRUIT = 'Fruit'
        VEGETABLE = 'Vegetable'

    @prompt_fn
    def classify_fruits(food: str) -> Food:
        ''' 
            Expertly determines the class label of {{food}}.
        '''
    ```

    This function can now be run and serialized to an Azure / OpenAI Function Calling payload.

    ??? success "Click to see results: ```classify_fruits('tomato').serialize()```"
        ```python
        {
        "messages": [
            {
            "role": "system",
            "content": "Expertly determines the class label of tomato."
            }
        ],
        "functions": [
            {
            "parameters": {
                "type": "object",
                "properties": {
                "output": {
                    "$ref": "#/definitions/Food"
                }
                },
                "required": [
                "output"
                ],
                "definitions": {
                "Food": {
                    "title": "Food",
                    "description": "Food classes",
                    "enum": [
                    "Fruit",
                    "Vegetable"
                    ]
                }
                }
            },
            "name": "Output",
            "description": ""
            }
        ],
        "function_call": {
            "name": "Output"
        }
        }   
        ```

### Entity Extraction

!!! Example 

    In this example, Marvin is configured to perform entity extraction on a list of fruits mentioned in a text string. The function `extract_fruits` identifies and extracts fruit entities based on the input text. These entities are then returned as a list of Pydantic models.

    ```python
    from marvin.prompts import prompt_fn
    from typing import List
    from pydantic import BaseModel

    class FruitEntity(BaseModel):
        '''
            Extracted Fruit Entities
        '''
        name: str
        color: str

    @prompt_fn
    def extract_fruits(text: str) -> List[FruitEntity]:
        ''' 
            Extracts fruit entities from the given text: {{text}}.
        '''
    ```

    This function can now be run and serialized to an Azure / OpenAI Function Calling payload.

    ??? success "```extract_fruits('There are red apples and yellow bananas.').serialize()```"
        ```python
        {
            "messages": [
                {
                "role": "system",
                "content": "Extracts fruit entities from the given text: There are red apples and yellow bananas.."
                }
            ],
            "functions": [
                {
                "parameters": {
                    "type": "object",
                    "properties": {
                    "output": {
                        "title": "Output",
                        "type": "array",
                        "items": {
                        "$ref": "#/definitions/FruitEntity"
                        }
                    }
                    },
                    "required": [
                    "output"
                    ],
                    "definitions": {
                    "FruitEntity": {
                        "title": "FruitEntity",
                        "description": "Extracted Fruit Entities",
                        "type": "object",
                        "properties": {
                        "name": {
                            "title": "Name",
                            "type": "string"
                        },
                        "color": {
                            "title": "Color",
                            "type": "string"
                        }
                        },
                        "required": [
                        "name",
                        "color"
                        ]
                    }
                    }
                },
                "name": "Output",
                "description": ""
                }
            ],
            "function_call": {
                "name": "Output"
            }
            }
        ```