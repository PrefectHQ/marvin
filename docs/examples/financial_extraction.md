
!!! Question "What is Financial Information Extraction?"
    Extracting financial information involves identifying and normalizing financial entities like currencies, stock symbols, and company names in a given text. For example:

    > "Apple's stock (AAPL) rose by 5% to $150, while Amazon (AMZN) fell to $3,100. EUR/USD exchange rate is 1.2."

    The challenge is to extract and interpret these financial entities accurately.

    How can we achieve a structured output like:

    ```python
    [
        Stock(text='AAPL', company='Apple', change='rose', percentage='5%', price='$150'),
        Stock(text='AMZN', company='Amazon', change='fell', price='$3,100'),
        CurrencyPair(text='EUR/USD', rate='1.2')
    ]
    ```

    This example will guide you through extracting and normalizing financial data from text.

## Creating our Data Model

To manage this financial data, we need a structured data model. We'll create two models: one for stock information and another for currency pairs.

```python
import pydantic

class Stock(pydantic.BaseModel):
    '''
        A model to represent stock information.
    '''

    text: str = pydantic.Field(description='The stock symbol as it appears')
    company: str = pydantic.Field(description='The associated company name')
    change: str = pydantic.Field(description='Stock price change direction')
    percentage: str = pydantic.Field(description='Change percentage', default=None)
    price: str = pydantic.Field(description='Current stock price')

class CurrencyPair(pydantic.BaseModel):
    '''
        A model to represent a currency pair exchange rate.
    '''

    text: str = pydantic.Field(description='Currency pair as it appears')
    rate: str = pydantic.Field(description='Exchange rate')
```

## Creating our Prompt

Next, we'll use Marvin's `prompt_fn` to create a function for processing the text.

```python
from marvin import prompt_fn
from typing import Union

@prompt_fn
def extract_financial_data(text: str) -> list[Union[Stock, CurrencyPair]]:
    '''
        Accurately extract all financial data from the following text: {{text}}
    '''

```

???+ "What does extract_financial_data do under the hood?"

    `extract_financial_data` translates the query into a format that a large language model understands. 

    Here's how it looks with our financial text:

    ```python
    extract_financial_data(
        "Apple's stock (AAPL) rose by 5% to $150, while Amazon (AMZN)"
        " fell to $3,100. EUR/USD exchange rate is 1.2."
    )
    ```
    ??? "Click to see output"

        ```json
        {
            "tools": [
                {
                "type": "function",
                "function": {
                    "name": "FormatResponse",
                    "description": "Formats the response.",
                    "parameters": {
                    "$defs": {
                        "CurrencyPair": {
                        "description": "A model to represent a currency pair exchange rate.",
                        "properties": {
                            "text": {
                            "description": "Currency pair as it appears",
                            "title": "Text",
                            "type": "string"
                            },
                            "rate": {
                            "description": "Exchange rate",
                            "title": "Rate",
                            "type": "string"
                            }
                        },
                        "required": [
                            "text",
                            "rate"
                        ],
                        "title": "CurrencyPair",
                        "type": "object"
                        },
                        "Stock": {
                        "description": "A model to represent stock information.",
                        "properties": {
                            "text": {
                            "description": "The stock symbol as it appears",
                            "title": "Text",
                            "type": "string"
                            },
                            "company": {
                            "description": "The associated company name",
                            "title": "Company",
                            "type": "string"
                            },
                            "change": {
                            "description": "Stock price change direction",
                            "title": "Change",
                            "type": "string"
                            },
                            "percentage": {
                            "default": null,
                            "description": "Change percentage",
                            "title": "Percentage",
                            "type": "string"
                            },
                            "price": {
                            "description": "Current stock price",
                            "title": "Price",
                            "type": "string"
                            }
                        },
                        "required": [
                            "text",
                            "company",
                            "change",
                            "price"
                        ],
                        "title": "Stock",
                        "type": "object"
                        }
                    },
                    "properties": {
                        "data": {
                        "description": "The data to format.",
                        "items": {
                            "anyOf": [
                            {
                                "$ref": "#/$defs/Stock"
                            },
                            {
                                "$ref": "#/$defs/CurrencyPair"
                            }
                            ]
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
                "content": "Accurately extract all financial data from the following text: Apple's stock (AAPL) rose by 5% to $150, while Amazon (AMZN) fell to $3,100. EUR/USD exchange rate is 1.2.",
                "role": "system"
                }
            ]
            }
        ```

## Calling our Language Model

We'll now process the text through the Large Language Model:

```python
import openai
import json

client = openai(api_key = 'YOUR OPENAI KEY')

response = client.chat.completions.create(
    model = 'gpt-3.5-turbo',
    temperature = 0,
    **extract_financial_data(
        "Apple's stock (AAPL) rose by 5% to $150, while Amazon (AMZN)"
        " fell to $3,100. EUR/USD exchange rate is 1.2."
    )
)
```
We can parse the raw response to extract the structured financial data:

```python
from pydantic import TypeAdapter

TypeAdapter(list[Union[Stock, CurrencyPair]]).validate_json(
    tool_calls[0].function.arguments
)
```

The output will be an array of Stock and CurrencyPair objects, neatly organizing the financial information.

```python
[
    Stock(text='AAPL', company='Apple', change='rose', percentage='5%', price='$150'),
    Stock(text='AMZN', company='Amazon', change='fell', price='$3,100'),
    CurrencyPair(text='EUR/USD', rate='1.2')
]
```
