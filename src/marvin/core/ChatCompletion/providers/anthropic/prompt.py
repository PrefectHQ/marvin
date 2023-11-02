import json
import re
from typing import Any, Literal, Optional, Union

from jinja2 import Environment
from marvin.utilities.strings import jinja_env

from ...utils import parse_raw

FUNCTION_PROMPT = """
# Functions

You can call various functions to perform tasks.

Whenever you receive a message from the user, check to see if any of your
functions would help you respond. For example, you might use a function to look
up information, interact with a filesystem, call an API, or validate data. You
might write code, update state, or cause a side effect. After indicating that
you want to call a function, the user will execute the function and tell you its
result so that you can use the information in your final response. Therefore,
you must use your functions whenever they would be helpful.

The user may also provide a `function_call` instruction which could be:

- "auto": you may decide to call a function on your own (this is the
    default)
- "none": do not call any function
- {"name": "<function-name>"}: you MUST call the function with the given
    name

To call a function:

- Your response must include a JSON payload with the below format, including the
  {"mode": "function_call"} key.
- Do not put any other text in your response beside the JSON payload.
- Do not describe your plan to call the function to the user; they will not see
  it. 
- Do not include more than one payload in your response.
- Do not include function output or results in your response.
    
# Available Functions

You have access to the following functions. Each has a name (which must be part
of your response), a description (which you should use to decide whether to call the
function), and a parameter spec (which is a JSON Schema description of the
arguments you should pass in your response)

{% for function in functions -%} 

## {{ function.name }} 

- Name: {{ function.name }} 
- Description: {{ function.description }} 
- Parameters: {{ function.parameters }}

{% endfor %}

# Calling a Function

To call a function, your response MUST include a JSON document with the
following structure: 

{
    "mode": "function_call", 
    
    "name": "<the name of the function, must be one of the above names>", 
    
    "arguments": "<a JSON string with the arguments to the function as valid
    JSON>"
}

The user will execute the function and respond with its result verbatim.

# function_call instruction

The user provided the following `function_call` instruction: {{ function_call }}

# final_response instruction

When you choose to call no functions, your final answer should be summative.
Do not acknowledge any internal functions you had access to or chose to call.

"""


def render_anthropic_functions_prompt(
    functions: list[dict[str, Any]],
    function_call: Union[dict[Literal["name"], str], Literal["auto"]],
    environment: Optional[Environment] = None,
) -> str:
    env = environment or jinja_env
    template = env.from_string(FUNCTION_PROMPT)
    return template.render(functions=functions, function_call=function_call or "auto")


def handle_anthropic_response(
    completion: str,
) -> tuple[Optional[str], Optional[dict[str, Any]]]:
    try:
        response: dict[str, Any] = parse_raw(
            re.findall(r"\{.*\}", completion, re.DOTALL)[0]
        )
        if response.pop("mode", None) == "function_call":
            return None, {
                "name": response.pop("name", None),
                "arguments": json.dumps(response.pop("arguments", None)),
            }
    except Exception:
        pass
    return completion, None
