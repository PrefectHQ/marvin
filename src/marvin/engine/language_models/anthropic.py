import inspect
import json
import re
from logging import Logger
from typing import Callable, Union

import anthropic
import openai
import openai.openai_object

import marvin
import marvin.utilities.types
from marvin.engine.language_models import ChatLLM, StreamHandler
from marvin.engine.language_models.base import OpenAIFunction
from marvin.models.messages import Message, Role
from marvin.utilities.async_utils import create_task
from marvin.utilities.logging import get_logger
from marvin.utilities.strings import jinja_env

FUNCTION_CALL_REGEX = re.compile(
    r'{\s*"mode":\s*"functions"\s*(.*)}',
    re.DOTALL,
)
FUNCTION_CALL_NAME = re.compile(r'"name":\s*"(.*)"')
FUNCTION_CALL_ARGS = re.compile(r'"arguments":\s*(".*")', re.DOTALL)


def extract_function_call(completion: str) -> Union[dict, None]:
    function_call = dict(name=None, arguments="{}")
    if match := FUNCTION_CALL_REGEX.search(completion):
        if name := FUNCTION_CALL_NAME.search(match.group(1)):
            function_call["name"] = name.group(1)
        if args := FUNCTION_CALL_ARGS.search(match.group(1)):
            function_call["arguments"] = args.group(1)
            try:
                function_call["arguments"] = json.loads(function_call["arguments"])
            except json.JSONDecodeError:
                pass
    if not function_call["name"]:
        return None
    return function_call


def anthropic_role_map(marvin_role: Role):
    if marvin_role in [Role.USER, Role.SYSTEM, Role.FUNCTION_RESPONSE]:
        return anthropic.HUMAN_PROMPT
    else:
        return anthropic.AI_PROMPT


class AnthropicStreamHandler(StreamHandler):
    async def handle_streaming_response(
        self,
        api_response: openai.openai_object.OpenAIObject,
    ) -> Message:
        """
        Accumulate chunk deltas into a full response. Returns the full message.
        Passes partial messages to the callback, if provided.
        """
        response = {
            "role": Role.ASSISTANT,
            "content": "",
            "data": {},
            "llm_response": None,
        }

        async for msg in api_response:
            response["llm_response"] = msg.dict()
            response["content"] += msg["completion"]

            if function_call := extract_function_call(msg):
                response["role"] = Role.FUNCTION_REQUEST
                response["data"]["function_call"] = function_call

            if self.callback:
                callback_result = self.callback(Message(**response))
                if inspect.isawaitable(callback_result):
                    create_task(callback_result)

        response["content"] = response["content"].strip()
        return Message(**response)


class AnthropicChatLLM(ChatLLM):
    def format_messages(
        self, messages: list[Message]
    ) -> Union[str, dict, list[Union[str, dict]]]:
        formatted_messages = []
        for msg in messages:
            role = anthropic_role_map(msg.role)
            formatted_messages.append(f"{role}{msg.content}")

        return "".join(formatted_messages) + anthropic.AI_PROMPT

    async def run(
        self,
        messages: list[Message],
        *,
        functions: list[OpenAIFunction] = None,
        function_call: Union[str, dict[str, str]] = None,
        logger: Logger = None,
        stream_handler: Callable[[Message], None] = False,
        **kwargs,
    ) -> Message:
        """Calls an OpenAI LLM with a list of messages and returns the response."""

        if logger is None:
            logger = get_logger(self.name)

        # ----------------------------------
        # Prepare functions
        # ----------------------------------
        if functions:
            function_message = jinja_env.from_string(
                FUNCTIONS_INSTRUCTIONS
                # Functions
            ).render(functions=functions, function_call=function_call)
            system_message = Message(role=Role.SYSTEM, content=function_message)
            messages = [system_message] + messages

        prompt = self.format_messages(messages)

        # ----------------------------------
        # Call OpenAI LLM
        # ----------------------------------

        if not marvin.settings.anthropic_api_key:
            raise ValueError(
                "Anthropic API key not found in settings. Please set it or use the"
                " MARVIN_ANTHROPIC_API_KEY environment variable."
            )

        client = anthropic.AsyncAnthropic(
            api_key=marvin.settings.anthropic_api_key.get_secret_value(),
        )

        response = await client.completions.create(
            model=self.model,
            prompt=prompt,
            max_tokens_to_sample=self.max_tokens,
            temperature=self.temperature,
            stream=True if stream_handler else False,
            **kwargs,
        )

        if stream_handler:
            handler = AnthropicStreamHandler(callback=stream_handler)
            msg = await handler.handle_streaming_response(response)
            return msg

        else:
            llm_response = response.dict()
            content = llm_response["completion"].strip()
            role = Role.ASSISTANT
            data = {}
            if function_call := extract_function_call(content):
                role = Role.FUNCTION_REQUEST
                data["function_call"] = function_call
            msg = Message(
                role=role,
                content=content,
                data=data,
                llm_response=llm_response,
            )
            return msg


FUNCTIONS_INSTRUCTIONS = """
# Functions

You can call functions to perform tasks that are beyond your base abilities.

The user may provide a `function_call` instruction which could be:
    - "auto": you may decide to call a function on your own (this is the
      default)
    - "none": do not call any function
    - {"name": "<function-name>"}: you MUST call the function with the given
      name

If `function_call` is "auto", decide whether to call a function by first
determining if the user's query requires information or services that are beyond
your base knowledge or capabilities. If you're not sure, then you should call a
function. Next, match the user's query to the appropriate function(s) based on
functionality and the type of information or service requested.

If you decide to call a function: 

- Your response must include a JSON payload with the below format, including the
  `"mode": "functions"` key-value pair. The presence of this key-value pair will
  indicate to the user that you have called a function.
- Do not put any additional information in your response. The function payload
  will be extracted, and the user will run the function and return the result to
  you. Neither you nor the user will remember calling the function, you will
  only see the result.
- Do not include or speculate about the function output after generating a
  payload.

Examples:
    - functions could interact with external services (send_email(to: string,
      body: string), get_current_weather(location: string, unit: 'celsius' |
      'fahrenheit'))
    - functions could validate data (validate_data(x: int, y: str) or
      validate_data(data: object))
    - functions could manage state (update_state(key:str, value: object))
    - functions could convert language to API calls ("Who are my top customers?"
      becomes get_customers(min_revenue: int, created_before: string, limit:
      int))

# Available Functions

Your have access to the following functions:

{% for function in functions %} 

## {{ function.name }} 

- Name: {{ function.name }}
- Description: {{ function.description }}
- Parameters: {{ function.parameters }}

{% endfor %}

# Calling a Function

To call a function, your response must include a JSON document with the
following structure: 

{
    "mode": "functions",
    
    "function_call": {
        "name": "<the name of the function, must be one of the above names>",
        "arguments": "<a JSON string with the arguments to the function as valid
        JSON>"
    }
}

Include ONLY this JSON object in your response. If this object is present, the
rest of your response will be ignored. The user will execute the function and
respond with its result verbatim.

# Function Call instruction

The user provided the following `function_call` instruction: {{ function_call }}
"""
