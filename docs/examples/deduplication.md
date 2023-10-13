
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

???+ "What does get_cities do under the hood?"

    Marvin's `prompt_fn` only creates a prompt to send to a large language model. It does not call any 
    external service, it's simply responsible for translating your query into something that a 
    large language model will understand. 

    Here's the output when we plug in our sentence from above:

    ```python
    get_cities("Chicago, The Windy City, New York City, the Big Apple, SF, San Fran, San Francisco.")
    ```
    ??? "Click to see output"

        ```json
        {
        "messages": [
            {
            "role": "system",
            "content": "Expertly deduce and infer all cities from the follwing text: Chicago, The Windy City, New York City, the Big Apple, SF, San Fran, San Francisco."
            }
        ],
        "functions": [
            {
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
                "output": {
                    "items": {
                    "$ref": "#/$defs/City"
                    },
                    "title": "Output",
                    "type": "array"
                }
                },
                "required": [
                "output"
                ],
                "type": "object"
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


## Calling our Language Model

Let's see what happens when we actually call our Large Language Model. Below, ``**`` tells let's us pass the prompt's parameters into our call to OpenAI.

```python
import openai
import json

response = openai.ChatCompletion.create(
    api_key = 'YOUR OPENAI KEY',
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

??? "View the raw response"
    The raw response we receive looks like 
    ```json
    {
        "id": "omitted for this example",
        "object": "chat.completion",
        "created": 1697222527,
        "model": "gpt-3.5-turbo-0613",
        "choices": [
            {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": null,
                "function_call": {
                "name": "Output",
                "arguments": "{\n  \"output\": [\n    {\n      \"text\": \"Chicago\",\n      \"inferred_city\": \"Chicago\"\n    },\n    {\n      \"text\": \"The Windy City\",\n      \"inferred_city\": \"Chicago\"\n    },\n    {\n      \"text\": \"New York City\",\n      \"inferred_city\": \"New York City\"\n    },\n    {\n      \"text\": \"The Big Apple\",\n      \"inferred_city\": \"New York City\"\n    },\n    {\n      \"text\": \"SF\",\n      \"inferred_city\": \"San Francisco\"\n    },\n    {\n      \"text\": \"San Fran\",\n      \"inferred_city\": \"San Francisco\"\n    },\n    {\n      \"text\": \"San Francisco\",\n      \"inferred_city\": \"San Francisco\"\n    }\n  ]\n}"
                }
            },
            "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": 87,
            "completion_tokens": 165,
            "total_tokens": 252
        }
    }
    ```

We can parse the raw response and mine out the relevant responses, 

```python
[
    City.parse_obj(city) 
    for city in 
    json.loads(
        response.choices[0].message.function_call.arguments
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

??? Copy the full example
    ```python

    import openai
    import json
    import pydantic
    from marvin import prompt_fn

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

    @prompt_fn
    def get_cities(text: str) -> list[City]:
        '''
            Expertly deduce and infer all cities from the follwing text: {{text}}
        '''

    response = openai.ChatCompletion.create(
        api_key = 'YOUR OPENAI KEY',
        model = 'gpt-3.5-turbo',
        temperature = 0,
        **get_cities(
            (
                "Chicago, The Windy City, New York City, "
                "The Big Apple, SF, San Fran, San Francisco."
            )
        )
    )

    [
        City.parse_obj(city) 
        for city in 
        json.loads(
            response.choices[0].message.function_call.arguments
        ).get('output')
    ]

    ```