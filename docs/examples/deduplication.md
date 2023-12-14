
!!! Question "What is entity deduplication?"
    How many distinct cities are mentioned in the following text:
    > Chicago, The Windy City, New York City, the Big Apple, SF, San Fran, San Francisco. 

    We know it's three, but getting software to deduplicate these entities is surprisingly hard. 
    
    How can we turn it into something cleaner like:

    ```python
    [
        City(text='Chicago', inferred_city='Chicago'),
        City(text='The Windy City', inferred_city='Chicago'),
        City(text='New York City', inferred_city='New York City'),
        City(text='The Big Apple', inferred_city='New York City'),
        City(text='SF', inferred_city='San Francisco'),
        City(text='San Fran', inferred_city='San Francisco'),
        City(text='San Francisco', inferred_city='San Francisco')
    ]
    ```
    
    In this example, we'll explore how you can do text and entity deduplication from a piece of text. 



## Creating our data model

To extract and deduplicate entities, we'll want to think carefully about the data we want to extract from this text. We clearly want a `list` of `cities`. So we'll want to create a data model to represent a city. But we won't stop there: 
we don't want to just get a list of cities that appear in the text. We want to get an *mapping* or *understanding* that SF is the same as San Francisco, and the Big Apple is the same as New York City, etc. 

```python

import pydantic

class City(pydantic.BaseModel):
    '''
        A model to represent a city.
    '''

    text: str = pydantic.Field(
        description = 'The city name as it appears'
    )

    inferred_city: str = pydantic.Field(
            description = 'The inferred and normalized city name.'
        )
```

## Creating our prompt

Now we'll need to use this model and convert it into a prompt we can send to a language model. We'll use Marvin's
prompt_fn to let us write a prompt like a python function. 

```python

from marvin import prompt_fn

@prompt_fn
def get_cities(text: str) -> list[City]:
    '''
        Expertly deduce and infer all cities from the follwing text: {{text}}
    '''

```

???+ question "What does get_cities do under the hood?"

    Marvin's `prompt_fn` only creates a prompt to send to a large language model. It does not call any 
    external service, it's simply responsible for translating your query into something that a 
    large language model will understand. 

    Here's the output when we plug in our sentence from above:

    ```python
    get_cities("Chicago, The Windy City, New York City, the Big Apple, SF, San Fran, San Francisco.")
    ```
    ??? info "Click to see output"

        ```json
        {
            "tools": [
                {
                "type": "function",
                "function": {
                    "name": "FormatResponse",
                    "parameters": {
                    "$defs": {
                        "City": {
                        "description": "A model to represent a city.",
                        "properties": {
                            "text": {
                            "description": "The city name as it appears",
                            "title": "Text",
                            "type": "string"
                            },
                            "inferred_city": {
                            "description": "The inferred and normalized city name.",
                            "title": "Inferred City",
                            "type": "string"
                            }
                        },
                        "required": [
                            "text",
                            "inferred_city"
                        ],
                        "title": "City",
                        "type": "object"
                        }
                    },
                    "properties": {
                        "data": {
                        "description": "The data to format.",
                        "items": {
                            "$ref": "#/$defs/City"
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
                "content": "
                    Expertly deduce and infer all cities from the follwing text: 
                    Chicago, The Windy City, New York City, the Big Apple, SF, 
                    San Fran, San Francisco.
                    ",
                "role": "system"
                }
            ]
            }   
        ```


## Calling our Language Model

Let's see what happens when we actually call our Large Language Model. Below, ``**`` tells let's us pass the prompt's parameters into our call to OpenAI.

```python
from openai import OpenAI
import json

client = OpenAI(api_key = 'YOUR_OPENAI_KEY')

response = client.chat.completions.create(
    model = 'gpt-3.5-turbo',
    temperature = 0,
    **get_cities(
        (
            "Chicago, The Windy City, New York City, "
            "The Big Apple, SF, San Fran, San Francisco."
        )
    )
)
```

??? info "View the raw response"
    The raw response we receive looks like 
    ```json
    {
    "id": "chatcmpl-id-number",
    "choices": [
        {
        "finish_reason": "stop",
        "index": 0,
        "message": {
            "content": null,
            "role": "assistant",
            "function_call": null,
            "tool_calls": [
            {
                "id": "call-id-number",
                "function": {
                "arguments": "{\n  \"data\": [\n    {\n      \"text\": \"Chicago\",\n      \"inferred_city\": \"Chicago\"\n    },\n    {\n      \"text\": \"The Windy City\",\n      \"inferred_city\": \"Chicago\"\n    },\n    {\n      \"text\": \"New York City\",\n      \"inferred_city\": \"New York City\"\n    },\n    {\n      \"text\": \"The Big Apple\",\n      \"inferred_city\": \"New York City\"\n    },\n    {\n      \"text\": \"SF\",\n      \"inferred_city\": \"San Francisco\"\n    },\n    {\n      \"text\": \"San Fran\",\n      \"inferred_city\": \"San Francisco\"\n    },\n    {\n      \"text\": \"San Francisco\",\n      \"inferred_city\": \"San Francisco\"\n    }\n  ]\n}",
                "name": "FormatResponse"
                },
                "type": "function"
            }
            ]
        }
        }
    ],
    "created": 1702591915,
    "model": "gpt-3.5-turbo-0613",
    "object": "chat.completion",
    "system_fingerprint": null,
    "usage": {
        "completion_tokens": 165,
        "prompt_tokens": 95,
        "total_tokens": 260
    }
    }   
    ```

We can parse the raw response and mine out the relevant responses, 

```python
[
    City(**city)
    for city in 
    json.loads(
        response.choices[0].message.tool_calls[0].function.arguments
    ).get('output')
]
```

what we'll get now is the pairs of raw, observed city and cleaned deduplicated city.

```python
[
    City(text='Chicago', inferred_city='Chicago'),
    City(text='The Windy City', inferred_city='Chicago'),
    City(text='New York City', inferred_city='New York City'),
    City(text='The Big Apple', inferred_city='New York City'),
    City(text='SF', inferred_city='San Francisco'),
    City(text='San Fran', inferred_city='San Francisco'),
    City(text='San Francisco', inferred_city='San Francisco')
]
```

So, we've seen that deduplicating data with a Large Language Model is fairly straightforward
in a customizable way using Marvin. If you want the entire content of the cells above in 
one place, you can copy the cell below.
