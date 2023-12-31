# Quickstart

After [installing Marvin](../installation), the fastest way to get started is by using one of Marvin's high-level [AI components](../../components/overview). These components are designed to integrate AI into abstractions you already know well, creating the best possible opt-in developer experience.

!!! info "Initializing a Client"
    To use Marvin you must have an API Key configured for an external model provider, like OpenAI. 
    
    You can pass your API Key to Marvin in one of two ways:

    - Set the environment variable `MARVIN_OPENAI_API_KEY` in `~/.marvin/.env` or as `OPENAI_API_KEY` in your shell config file.

    ```shell
    » cat ~/.marvin/.env | rg OPENAI
    MARVIN_OPENAI_API_KEY=sk-xxx
    MARVIN_OPENAI_ORGANIZATION=org-xxx
    ```

    - Pass your API Key to Marvin's `OpenAI` client constructor. 

    ```python
    from openai import OpenAI

    client = OpenAI(api_key = 'YOUR_API_KEY')
    ```

## Components 

### AI Models

Marvin's most basic component is the AI Model, built on Pydantic's `BaseModel`. AI Models can be instantiated from any string, making them ideal for structuring data and entity extraction.

!!! example "Example"
    === "As a decorator"
        `ai_model` can decorate pydantic models to give them parsing powers.
        ```python
        from marvin import ai_model
        from pydantic import BaseModel, Field

        @ai_model
        class Location(BaseModel):
            city: str
            state_abbreviation: str = Field(
                ..., 
                description="The two-letter state abbreviation"
            )


        Location("The Big Apple")
        ```
        ??? info "Generated Prompt"
            You can view and/or eject the generated prompt by simply calling 
            ```python
            Location.as_prompt().serialize()
            ```
            When you do you'll see the raw payload that's sent to the LLM. All of the parameters
            below like `FormatResponse` and the prompt you send are fully customizable. 

            ```json
             {
                "tools": [
                    {
                    "type": "function",
                    "function": {
                        "name": "FormatResponse",
                        "parameters": {
                        "$defs": {
                            "Location": {
                            "properties": {
                                "city": {
                                "title": "City",
                                "type": "string"
                                },
                                "state_abbreviation": {
                                "description": "The two-letter state abbreviation",
                                "title": "State Abbreviation",
                                "type": "string"
                                }
                            },
                            "required": [
                                "city",
                                "state_abbreviation"
                            ],
                            "title": "Location",
                            "type": "object"
                            }
                        },
                        "properties": {
                            "data": {
                            "allOf": [
                                {
                                "$ref": "#/$defs/Location"
                                }
                            ],
                            "description": "The data to format."
                            }
                        },
                        "required": [
                            "data"
                        ],
                        "type": "object"
                        }
                    }
                    }
                ],
                "tool_choice": {
                    "type": "function",
                    "function": {
                    "name": "FormatResponse"
                    }
                },
                "messages": [
                    {
                    "content": "The user will provide context as text that you need to parse
                    into a structured form. To validate your response, you must call the 
                    `FormatResponse` function. Use the provided text to extract or infer any 
                    parameters needed by `FormatResponse`, including any missing data.",
                    "role": "system"
                    },
                    {
                    "content": "The text to parse: The Big Apple",
                    "role": "user"
                    }
                ]
            }
            ```

    === "As a function"
        `ai_model` can cast unstructured data to any `type` (or `GenericAlias`).
        ```python
        from marvin import ai_model
        from pydantic import BaseModel, Field

        class Location(BaseModel):
            city: str
            state_abbreviation: str = Field(
                ..., 
                description="The two-letter state abbreviation"
            )

        ai_model(Location)("The Big Apple")
        ```
        ??? info "Generated Prompt"
            You can view and/or eject the generated prompt by simply calling 
            ```python
            ai_model(Location)("The Big Apple").as_prompt().serialize()
            ```
            When you do you'll see the raw payload that's sent to the LLM. All of the parameters
            below like `FormatResponse` and the prompt you send are fully customizable. 

            ```json
                {
                "tools": [
                    {
                    "type": "function",
                    "function": {
                        "name": "FormatResponse",
                        "parameters": {
                        "$defs": {
                            "Location": {
                            "properties": {
                                "city": {
                                "title": "City",
                                "type": "string"
                                },
                                "state_abbreviation": {
                                "description": "The two-letter state abbreviation",
                                "title": "State Abbreviation",
                                "type": "string"
                                }
                            },
                            "required": [
                                "city",
                                "state_abbreviation"
                            ],
                            "title": "Location",
                            "type": "object"
                            }
                        },
                        "properties": {
                            "data": {
                            "allOf": [
                                {
                                "$ref": "#/$defs/Location"
                                }
                            ],
                            "description": "The data to format."
                            }
                        },
                        "required": [
                            "data"
                        ],
                        "type": "object"
                        }
                    }
                    }
                ],
                "tool_choice": {
                    "type": "function",
                    "function": {
                    "name": "FormatResponse"
                    }
                },
                "messages": [
                    {
                    "content": "The user will provide context as text that you need to parse
                    into a structured form. To validate your response, you must call the 
                    `FormatResponse` function. Use the provided text to extract or infer any 
                    parameters needed by `FormatResponse`, including any missing data.",
                    "role": "system"
                    },
                    {
                    "content": "The text to parse: The Big Apple",
                    "role": "user"
                    }
                ]
            }
            ```
    !!! success "Result"
        ```python
        Location(city='New York', state='NY')
        ```

### AI Classifiers

AI Classifiers let you build multi-label classifiers with no code and no training data. Given user input, each classifier uses a [clever logit bias trick](https://twitter.com/AAAzzam/status/1669753721574633473) to force an LLM to deductively choose the best option. It's bulletproof, cost-effective, and lets you build classifiers as quickly as you can write your classes.

!!! example "Example"
    === "As a decorator"
        `ai_classifier` can decorate python functions whose return annotation is an `Enum` or `Literal`. The prompt is tuned for classification tasks, 
        and uses a form of `constrained sampling` to make guarantee a fast valid choice.
        ```python
        from marvin import ai_classifier
        from enum import Enum

        class AppRoute(Enum):
            """Represents distinct routes command bar for a different application"""

            USER_PROFILE = "/user-profile"
            SEARCH = "/search"
            NOTIFICATIONS = "/notifications"
            SETTINGS = "/settings"
            HELP = "/help"
            CHAT = "/chat"
            DOCS = "/docs"
            PROJECTS = "/projects"
            WORKSPACES = "/workspaces"

        @ai_classifier(client = client)
        def classify_intent(text: str) -> AppRoute:
            '''Classifies user's intent into most useful route'''

        classify_intent("update my name")
        ```
        ??? info "Generated Prompt"
            You can view and/or eject the generated prompt by simply calling 
            ```python
            classify_intent.as_prompt("update my name").serialize()
            ```
            When you do you'll see the raw payload that's sent to the LLM. The prompt you send is fully customizable. 
            ```json
            {
            "logit_bias": {
                "15": 100.0,
                "16": 100.0,
                "17": 100.0,
                "18": 100.0,
                "19": 100.0,
                "20": 100.0,
                "21": 100.0,
                "22": 100.0,
                "23": 100.0
            },
            "max_tokens": 1,
            "messages": [
                {
                "content": "## Expert Classifier\n\n        **Objective**: You are an expert classifier that always chooses correctly.\n\n        ### Context\n        Classifies user's intent into most useful route\n        \n        ### Response Format\n        You must classify the user provided data into one of the following classes:\n        - Class 0 (value: USER_PROFILE)\n        - Class 1 (value: SEARCH)\n        - Class 2 (value: NOTIFICATIONS)\n        - Class 3 (value: SETTINGS)\n        - Class 4 (value: HELP)\n        - Class 5 (value: CHAT)\n        - Class 6 (value: DOCS)\n        - Class 7 (value: PROJECTS)\n        - Class 8 (value: WORKSPACES)",
                "role": "system"
                },
                {
                "content": "### Data\n        The user provided the following data:                                                                                                                     \n        - text: update my name",
                "role": "assistant"
                },
                {
                "content": "The most likely class label for the data and context provided above is Class\"",
                "role": "assistant"
                }
            ],
            "temperature": 0.0
            }
            ```

    === "As a function"
        ```python
        from marvin import ai_classifier
        from enum import Enum

        class AppRoute(Enum):
            """Represents distinct routes command bar for a different application"""

            USER_PROFILE = "/user-profile"
            SEARCH = "/search"
            NOTIFICATIONS = "/notifications"
            SETTINGS = "/settings"
            HELP = "/help"
            CHAT = "/chat"
            DOCS = "/docs"
            PROJECTS = "/projects"
            WORKSPACES = "/workspaces"

        def classify_intent(text: str) -> AppRoute:
            '''Classifies user's intent into most useful route'''

        ai_classifier(classify_intent, client = client)("update my name")
        ```
        ??? info "Generated Prompt"
            You can view and/or eject the generated prompt by simply calling 
            ```python
            ai_classifier(classify_intent, client = client).as_prompt("update my name").serialize()
            ```
            When you do you'll see the raw payload that's sent to the LLM. The prompt you send is fully customizable. 
            ```json
            {
                "logit_bias": {
                    "15": 100.0,
                    "16": 100.0,
                    "17": 100.0,
                    "18": 100.0,
                    "19": 100.0,
                    "20": 100.0,
                    "21": 100.0,
                    "22": 100.0,
                    "23": 100.0
                },
                "max_tokens": 1,
                "messages": [
                    {
                    "content": "## Expert Classifier\n\n        **Objective**: You are an expert classifier that always chooses correctly.\n\n        ### Context\n        Classifies user's intent into most useful route\n        \n        ### Response Format\n        You must classify the user provided data into one of the following classes:\n        - Class 0 (value: USER_PROFILE)\n        - Class 1 (value: SEARCH)\n        - Class 2 (value: NOTIFICATIONS)\n        - Class 3 (value: SETTINGS)\n        - Class 4 (value: HELP)\n        - Class 5 (value: CHAT)\n        - Class 6 (value: DOCS)\n        - Class 7 (value: PROJECTS)\n        - Class 8 (value: WORKSPACES)",
                    "role": "system"
                    },
                    {
                    "content": "### Data\n        The user provided the following data:                                                                                                                     \n        - text: update my name",
                    "role": "assistant"
                    },
                    {
                    "content": "The most likely class label for the data and context provided above is Class\"",
                    "role": "assistant"
                    }
                ],
                "temperature": 0.0
            }
            ```

    !!! success "Result"
        ```python
        <AppRoute.USER_PROFILE: '/user-profile'>
        ```

### AI Functions

AI Functions look like regular functions, but have no source code. Instead, an AI uses their description and inputs to generate their outputs, making them ideal for NLP applications like sentiment analysis.

!!! example "Example"
    === "As a decorator"
        `ai_fn` can decorate python functions to evlaute them using a Large Language Model.
        ```python
        from marvin import ai_fn

        @ai_fn
        def sentiment_list(texts: list[str]) -> list[float]:
            """
            Given a list of `texts`, returns a list of numbers between 1 (positive) and
            -1 (negative) indicating their respective sentiment scores.
            """


        sentiment_list(
            [
                "That was surprisingly easy!",
                "Oh no, not again.",
            ]
        )



        ```
        ??? info "Generated Prompt"
            You can view and/or eject the generated prompt by simply calling 
            ```python
            sentiment_list.as_prompt().serialize()
            ```
            When you do you'll see the raw payload that's sent to the LLM. All of the parameters
            below like `FormatResponse` and the prompt you send are fully customizable. 

            ```json
            {
            "tools": [
                {
                "type": "function",
                "function": {
                    "name": "FormatResponse",
                    "parameters": {
                    "properties": {
                        "data": {
                        "description": "The data to format.",
                        "items": {
                            "type": "number"
                        },
                        "title": "Data",
                        "type": "array"
                        }
                    },
                    "required": [
                        "data"
                    ],
                    "type": "object"
                    }
                }
                }
            ],
            "tool_choice": {
                "type": "function",
                "function": {
                "name": "FormatResponse"
                }
            },
            "messages": [
                {
                "content": "Your job is to generate likely outputs for a Python function with the\n        following signature and docstring:\n\n        \ndef sentiment_list(texts: list[str]) -> list[float]:\n    \"\"\"\n    Given a list of `texts`, returns a list of numbers between 1 (positive) and\n    -1 (negative) indicating their respective sentiment scores.\n    \"\"\"\n\n\n        The user will provide function inputs (if any) and you must respond with\n        the most likely result.",
                "role": "system"
                },
                {
                "content": "The function was called with the following inputs:\n        - texts: ['That was surprisingly easy!', 'Oh no, not again.']\n\n        What is its output?",
                "role": "user"
                }
            ]
            }
            ```

    === "As a function"
        `ai_fn` can be used as a utility function to evaluate python functions using a Large Language Model.
        ```python
        from marvin import ai_fn

        def sentiment_list(texts: list[str]) -> list[float]:
            """
            Given a list of `texts`, returns a list of numbers between 1 (positive) and
            -1 (negative) indicating their respective sentiment scores.
            """


        ai_fn(sentiment_list)(
            [
                "That was surprisingly easy!",
                "Oh no, not again.",
            ]
        )
        ```
        ??? info "Generated Prompt"
            You can view and/or eject the generated prompt by simply calling 
            ```python
            ai_fn(sentiment_list)([
                "That was surprisingly easy!",
                "Oh no, not again.",
            ]).as_prompt().serialize()
            ```
            When you do you'll see the raw payload that's sent to the LLM. All of the parameters
            below like `FormatResponse` and the prompt you send are fully customizable. 

            ```json
               {
                    "tools": [
                        {
                        "type": "function",
                        "function": {
                            "name": "FormatResponse",
                            "parameters": {
                            "properties": {
                                "data": {
                                "description": "The data to format.",
                                "items": {
                                    "type": "number"
                                },
                                "title": "Data",
                                "type": "array"
                                }
                            },
                            "required": [
                                "data"
                            ],
                            "type": "object"
                            }
                        }
                        }
                    ],
                    "tool_choice": {
                        "type": "function",
                        "function": {
                        "name": "FormatResponse"
                        }
                    },
                    "messages": [
                        {
                        "content": "Your job is to generate likely outputs for a Python function with the\n        following signature and docstring:\n\n        \ndef sentiment_list(texts: list[str]) -> list[float]:\n    \"\"\"\n    Given a list of `texts`, returns a list of numbers between 1 (positive) and\n    -1 (negative) indicating their respective sentiment scores.\n    \"\"\"\n\n\n        The user will provide function inputs (if any) and you must respond with\n        the most likely result.",
                        "role": "system"
                        },
                        {
                        "content": "The function was called with the following inputs:\n        - texts: ['That was surprisingly easy!', 'Oh no, not again.']\n\n        What is its output?",
                        "role": "user"
                        }
                    ]
                    }
            ```
    !!! success "Result"
        ```python
        [0.7, -0.5]
        ```

## Utilities
Every Marvin component makes use of two serialization conveniences, which you're free to use 
if you want to create your own opinionated components.

### Prompt Functions
Prompt Functions are responsible for taking a Python function and serializing it to a payload for a Large Language Model API to understand. It does not call
or require an LLM provider. It's essentially a type-safe Jinja template that makes the locals of your function available for template formatting. 

!!! example "Example"
    === "As a decorator"
        `prompt_fn` can decorate python functions to serialize them to a payload which them using a Large Language Model. It's especially useful
        if you want to use your own custom LLM but enjoy the ergonomics of Marvin.
        ```python

        from marvin import prompt_fn

        @prompt_fn
        def list_fruits(n: int, color: str = 'red') -> list[str]:
            """
            Generates a list of {{n}} {{color}} fruits.
            """


        list_fruits(3, 'blue')
        ```
        ??? success "Result"
            
            It generates the raw payload that can be sent to an LLM. All of the parameters
            below like `FormatResponse` and the prompt you send are fully customizable. 

            ```json
            {
            "tools": [
                {
                "type": "function",
                "function": {
                    "name": "FormatResponse",
                    "parameters": {
                    "properties": {
                        "data": {
                        "description": "The data to format.",
                        "items": {
                            "type": "string"
                        },
                        "title": "Data",
                        "type": "array"
                        }
                    },
                    "required": [
                        "data"
                    ],
                    "type": "object"
                    }
                }
                }
            ],
            "tool_choice": {
                "type": "function",
                "function": {
                "name": "FormatResponse"
                }
            },
            "messages": [
                {
                "content": "Generate a list of 3 blue fruits.",
                "role": "system"
                }
            ]
            }
            ```

    === "As a function"
        `prompt_fn` can be used as a utility function to seraizlie python functions to prompts for a Large Language Model. It's especially useful
        if you want to use your own custom LLM but enjoy the ergonomics of Marvin.
        ```python
        from marvin import prompt_fn

        def list_fruits(n: int, color: str = 'red') -> list[str]:
            """
            Generates a list of {{n}} {{color}} fruits.
            """


        prompt_fn(list_fruits)(3, 'blue')
        ```
        ??? success "Result"
            
            It generates the raw payload that can be sent to an LLM. All of the parameters
            below like `FormatResponse` and the prompt you send are fully customizable. 

            ```json
            {
            "tools": [
                {
                "type": "function",
                "function": {
                    "name": "FormatResponse",
                    "parameters": {
                    "properties": {
                        "data": {
                        "description": "The data to format.",
                        "items": {
                            "type": "string"
                        },
                        "title": "Data",
                        "type": "array"
                        }
                    },
                    "required": [
                        "data"
                    ],
                    "type": "object"
                    }
                }
                }
            ],
            "tool_choice": {
                "type": "function",
                "function": {
                "name": "FormatResponse"
                }
            },
            "messages": [
                {
                "content": "Generate a list of 3 blue fruits.",
                "role": "system"
                }
            ]
            }
            ```


### Response Models
For some applications, you may just want a helpful function calling utility instead of a full serialization layer. 
You can use Marvin to *wrap* your client and enable it to handle a `response_model` keyword argument, or simply rely on
our serialization / parsing primitives. Use whatever you need for your use case.

#### Marvin.wrap
Under the hood, Marvin uses a convenience wrapper around the OpenAI API to pass Pydantic models as a `response_model` keyword. This let's you 
use OpenAI to give you answers in a very specific way. 
!!! example 
    ```python
    from marvin.client import Marvin
    from marvin.client.openai import MarvinClient
    from openai import OpenAI
    from pydantic import BaseModel

    client = Marvin.wrap(OpenAI(api_key = 'YOUR_API_KEY'))

    class Coffee(BaseModel):
        '''A coffee order'''
        size: str
        with_milk: bool

    client.chat.completions.create(
        messages = [
            {
                'role': 'user', 
                'content': 'can I get a large latte?'
            }
        ], 
        response_model = Coffee
    )

    ```
    !!! success "Result"
        ```python
        Coffee(size='large', with_milk=True)
        ```

#### Pydantic 
The `Marvin.wrap` convenience is simply a wrapper around two utilities: `cast_model_to_toolset` and `cast_chat_completion_to_model`. As their names suggest each have
a simple function: converting your pydantic models to a set of tools to be used by a large language model, and one for converting your response back into that model.
!!! example 
    We can recreate the example above in parts. First we'll spread `**` the toolset to our vanilla LLM call, and then parse its response. Everything here is 
    rigorously typed so it plays well with type hinters.
    ```python
    from marvin._mappings.base_model import cast_model_to_toolset
    from marvin._mappings.chat_completion import cast_chat_completion_to_model
    from openai import OpenAI
    from pydantic import BaseModel

    class Coffee(BaseModel):
        '''A coffee order'''
        size: str
        with_milk: bool

    response = client.chat.completions.create(
        model = 'gpt-3.5-turbo',
        messages = [
            {
                'role': 'user', 
                'content': 'can I get a large latte?'
            }
        ], 
        **cast_model_to_toolset(Coffee).model_dump()
    )

    cast_chat_completion_to_model(Coffee, response)



    ```
    !!! success "Result"
        ```python
        Coffee(size='large', with_milk=True)
        ```