# Prompting with Code

Marvin offers a API for defining dynamic prompts with code. Instead of managing cumbersome template structures, you can define reusable and modular prompts with code.

```python
from marvin.prompts.library import System, User, Now, ChainOfThought

(
    System(content = "You're an expert at query planning.")
  | Now() # Give the LLM the current time
  | User( content = "I need to plan for an upcoming talk on plumbi.")
  | ChainOfThought() # Tell the LLM to think step by step
)
```

### MessagePrompt
The base class for message prompts, including options for specifying the role of the message, content, name, and priority of the message. Override the `get_content` method to customize behavior.

```python
class MessagePrompt(Prompt):
    ...
