# Marvin Tasks

Structured AI task definitions and execution framework for reliable, type-safe AI operations.

## Core Concepts

- **Task**: Declarative AI operation with clear inputs/outputs
- **Type Safety**: Full Pydantic validation of task parameters and results
- **Reliability**: Built-in retry logic and error handling
- **Composability**: Tasks can be chained and combined

## Task Types

- **Classification**: Categorize inputs into predefined classes
- **Extraction**: Pull structured data from unstructured text
- **Generation**: Create content based on specifications
- **Transformation**: Convert data from one format to another

## Usage Patterns

```python
from marvin import task

@task
def extract_contact_info(text: str) -> ContactInfo:
    """Extract contact information from text"""
    ...

# Task automatically handles AI interaction
result = extract_contact_info("Call John at 555-1234")
```

## Design Philosophy

- Tasks are pure functions with AI capabilities
- Type hints drive behavior and validation
- Docstrings provide context to the AI model
- Results are guaranteed to match return type annotations 