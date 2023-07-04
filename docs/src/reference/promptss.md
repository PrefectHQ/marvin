# Prompts as Code

Marvin introduces a API for defining dynamic prompts with code. Instead of managing cumbersome templates, you can define reusable and modular prompts with code. 

```python
from marvin.prompts.library import System, User, Now, ChainOfThought

full_prompt = (
    System("You're an expert on python.")
    | User("I need to know how to write a function in python.")
    | ChainOfThought()  # Tell the LLM to think step by step
)
```
Marvin's optional templating engine makes it dead-simple to share context across prompts. Pass native Python
types or Pydantic objects into the rendering engine to make entire conversations share context.

```python
from marvin.prompts.library import System, User, Now, ChainOfThought
from marvin.prompts import render_prompts

render_prompts(
    System("You're an expert on {{subject}}.")
    | User("I need to know how to write a function in {{subject}}.")
    | ChainOfThought(),  # Tell the LLM to think step by step,
    {"subject": "rust"},
)
```


###  Access, implement, test, and customize common LLM patterns. 
Marvin's prompt as code let's you hot-swap reasoning patterns for rapid development.

```python
from marvin.prompts.library import System

class ReActPattern(System):
  content = '''
    You run in a loop of Thought, Action, PAUSE, Observation.
    At the end of the loop you output an Answer
    Use Thought to describe your thoughts about the question you have been asked.
    Use Action to run one of the actions available to you - then return PAUSE.
    Observation will be the result of running those actions.
  '''

```


### Create custom prompts that can be shared, tested, and versioned.

Marvin provides simple, opinionated components so that you can subclass and customize
prompts the same way you would for code. 

```python
from marvin.prompts.library import System
import pydantic

class SQLTableDescription(System):
    content = '''
    If you chose to, you may query a table whose schema is defined below:
    
    {% for column in columns %}
    - {{ column.name }}: {{ column.description }}
    {% endfor %}
    '''

    columns: list[ColumnInfo] = pydantic.Field(
        ...,
        description='name, description pairs of SQL Schema'
    )

UserQueryPrompt = SQLTableDescription(
    columns = [
        ColumnInfo(name='last_login', description='Date and time of user\'s last login'),
        ColumnInfo(name='date_created', description='Date and time when the user record was created'),
        ColumnInfo(name='date_last_purchase', description='Date and time of user\'s last purchase'),
])
```

## Rendering Prompts

A chain of prompts is turned into messages with the `render_prompts` function. This funciton has a few responsibilities in addition to generating messages: it renders templates using runtime variables, sorts messages, and trims prompts to fit into a model's context window. The last two actions depend on the optional `position` and `priority` attributes of each prompt. 

For example, the `System` prompt defines `position=0` and `priority=1` to indicate that system prompts should be rendered first and given high priority when trimming the context. (As an optimization, `render_prompt` automatically combines multiple system messages into a single message.) `ChainOfThought()` has a `position=-1` to indicate it should be the last message. If position is not set explicitly, then prompts will take the order they are added to the chain. 

