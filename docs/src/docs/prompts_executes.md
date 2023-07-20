# Executing Prompts

Marvin makes executing `single-shot`, `chain`, or `agentic` behavior dead simple. 


## Running a `single-shot` prompt.

If you've crafted a prompt you'd like to fire off once and get the response, 
simply import a language model and hit run. 

```python
from marvin.prompts.library import System, ChainOfThought, User
from marvin.llms.providers import chat_llm
from marvin.prompts import render_prompts

await chat_llm().run(
    messages=render_prompts(
        System(content="You're an expert on {{subject}}.")
        | User(content="I need to know how to write a function in {{subject}}.")
        | ChainOfThought(),  # Tell the LLM to think step by step
        {"subject": "rust"},
    )
)

```

## Running a `chain`.

If you've crafted a prompt that you want to run in a loop -- so that it can deduce
its next actions and take them -- we've got you covered. Import an Executor and hit start.

```python
from marvin.prompts.library import System, ChainOfThought, User
from marvin.prompts import render_prompts

await chat_llm().run(
    messages=render_prompts(
        System(content="You're an expert on {{subject}}.")
        | User(content="I need to know how to write a function in {{subject}}.")
        | ChainOfThought(),  # Tell the LLM to think step by step
        {"subject": "rust"},
    )
)
```