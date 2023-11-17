!!! Question "What is Meeting Information Extraction?"
    Extracting essential information from meeting notes involves identifying action items, responsible individuals, deadlines, blockers, a summary of the meeting, and unresolved questions. For instance:

    > "In today's meeting, we discussed the marketing strategy. John will finalize the report by next Friday. There's a blocker: the budget approval from finance. Sarah raised a question about the new market entry which remains unresolved."

    The goal is to structure this information in an accessible format.

    A potential structured output:

    ```json
    {
        "action_items": [
            {
                "text": "finalize the marketing report", 
                "responsible": "John", 
                "deadline": "next Friday", 
                "blocker": "budget approval"
            }
        ],
        "meeting_summary": "Discussion on marketing strategy with key tasks assigned.",
        "unresolved_questions": [
            {
                "text": "Query about new market entry", 
                "raised_by": "Sarah"
            }
        ]
    }
    ```

    This example demonstrates how to process meeting notes for structured information extraction.

## Creating our Data Models

We'll begin by creating models for action items, meeting summary, and unresolved questions.

```python
import pydantic

class ActionItem(pydantic.BaseModel):
    '''
        A model to represent an action item from a meeting.
    '''

    text: str = pydantic.Field(
        description='Description of the action item'
    )
    responsible: str = pydantic.Field(
        description='Person responsible'
    )
    deadline: str = pydantic.Field(
        description='Deadline for completion', 
        default=None
    )
    blocker: str = pydantic.Field(
        description='Any blockers', 
        default=None
    )

class UnresolvedQuestion(pydantic.BaseModel):
    '''
        A model for unresolved questions raised during a meeting.
    '''

    text: str = pydantic.Field(
        description='The question raised'
        )
    raised_by: str = pydantic.Field(
        description='Person who raised the question'
        )
```

## Creating our Prompt

Next, we use Marvin's `prompt_fn` to create a function for processing the text.

```python
from marvin import prompt_fn

@prompt_fn
def extract_meeting_info(text: str) -> dict:
    '''
        Extract action items, summary, and unresolved questions
        from the following meeting notes: {{text}}
    '''

```

???+ "Functionality of extract_meeting_info"

    `extract_meeting_info` prepares the query for the language model. 

    Example usage:

    ```python
    extract_meeting_info(
        "In today's meeting, we discussed the marketing strategy. "
        " John will finalize the report by next Friday."
        " There's a blocker: the budget approval from finance."
        " Sarah raised a question about the new market entry which remains unresolved."
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
                    "ActionItem": {
                    "description": "A model to represent an action item from a meeting.",
                    "properties": {
                        "text": {
                        "description": "Description of the action item",
                        "title": "Text",
                        "type": "string"
                        },
                        "responsible": {
                        "description": "Person responsible",
                        "title": "Responsible",
                        "type": "string"
                        },
                        "deadline": {
                        "default": null,
                        "description": "Deadline for completion",
                        "title": "Deadline",
                        "type": "string"
                        },
                        "blocker": {
                        "default": null,
                        "description": "Any blockers",
                        "title": "Blocker",
                        "type": "string"
                        }
                    },
                    "required": [
                        "text",
                        "responsible"
                    ],
                    "title": "ActionItem",
                    "type": "object"
                    },
                    "UnresolvedQuestion": {
                    "description": "A model for unresolved questions raised during a meeting.",
                    "properties": {
                        "text": {
                        "description": "The question raised",
                        "title": "Text",
                        "type": "string"
                        },
                        "raised_by": {
                        "description": "Person who raised the question",
                        "title": "Raised By",
                        "type": "string"
                        }
                    },
                    "required": [
                        "text",
                        "raised_by"
                    ],
                    "title": "UnresolvedQuestion",
                    "type": "object"
                    }
                },
                "properties": {
                    "data": {
                    "description": "The data to format.",
                    "items": {
                        "anyOf": [
                        {
                            "$ref": "#/$defs/ActionItem"
                        },
                        {
                            "$ref": "#/$defs/UnresolvedQuestion"
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
            "content": "Extract action items, summary, and unresolved questions from the following meeting notes: In today's meeting, we discussed the marketing strategy. John will finalize the report by next Friday. There's a blocker: the budget approval from finance. Sarah raised a question about the new market entry which remains unresolved.",
            "role": "system"
            }
        ]
        }
        ```

## Processing Text with a Language Model

We now process the text through the Large Language Model using the updated SDK syntax:

```python
import openai
import json

client = openai.Client(api_key='YOUR OPENAI KEY')

response = client.chat.completions.create(
    model='gpt-3.5-turbo',
    temperature=0,
    **extract_meeting_info(
        "In today's meeting, we discussed the marketing strategy. "
        " John will finalize the report by next Friday."
        " There's a blocker: the budget approval from finance."
        " Sarah raised a question about the new market entry which remains unresolved."
    )
)
```

??? "View the raw response"
    The structured response from the language model.

Parsing the raw response for structured meeting information:

```python
from pydantic import TypeAdapter
from typing import Union

TypeAdapter(list[Union[ActionItem, UnresolvedQuestion]]).validate_json(
    response.function_call.arguments
)
```

The final output provides a clear and structured overview of the meeting's key points.

```json
{
    "action_items": [
        {
            "text": "finalize the marketing report", 
            "responsible": "John", 
            "deadline": "next Friday", 
            "blocker": "budget approval"
        }
    ],
    "meeting_summary": "Discussion on marketing strategy with key tasks assigned.",
    "unresolved_questions": [
        {
            "text": "Query about new market entry", 
            "raised_by": "Sarah"
        }
    ]
}
```

This method showcases how to effectively extract and structure important details from meeting notes using Marvin with an updated approach to using OpenAI's SDK.

??? Copy the full example
    ```python
    // Your full example code here
    ```

