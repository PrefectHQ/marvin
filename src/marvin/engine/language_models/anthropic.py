import inspect
import json
import re
from logging import Logger
from typing import Callable, Union

import anthropic
import openai
import openai.openai_object
from pydantic import BaseModel

import marvin
import marvin.utilities.types
from marvin.engine.language_models import ChatLLM, StreamHandler
from marvin.engine.language_models.base import OpenAIFunction
from marvin.utilities.async_utils import create_task
from marvin.utilities.logging import get_logger
from marvin.utilities.messages import Message, Role
from marvin.utilities.strings import jinja_env

CONTEXT_SIZES = {
    "claude-instant": 100_000,
    "claude-2": 100_000,
}

FUNCTION_CALL_REGEX = re.compile(
    r'{\s*"mode":\s*"function_call"\s*(.*)}',
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


class AnthropicFunctionCall(BaseModel):
    mode: str
    name: str
    arguments: str

    @classmethod
    def parse_raw(cls, raw: str):
        return super().parse_raw(re.sub("^[^{]*|[^}]*$", "", raw))


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
            response["content"] += msg.completion

            if function_call := extract_function_call(response["content"]):
                response["role"] = Role.FUNCTION_REQUEST
                response["data"]["function_call"] = function_call

            if self.callback:
                callback_result = self.callback(Message(**response))
                if inspect.isawaitable(callback_result):
                    create_task(callback_result)

        response["content"] = response["content"].strip()
        return Message(**response)


class AnthropicChatLLM(ChatLLM):
    model: str = "claude-2"

    @property
    def context_size(self) -> int:
        if self.model in CONTEXT_SIZES:
            return CONTEXT_SIZES[self.model]
        else:
            for model_prefix, context in CONTEXT_SIZES:
                if self.model.startswith(model_prefix):
                    return context
        return 100_000

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
            function_message = jinja_env.from_string(FUNCTIONS_INSTRUCTIONS).render(
                functions=functions, function_call=function_call
            )
            system_message = Message(role=Role.SYSTEM, content=function_message)
            messages = [system_message] + messages

        prompt = self.format_messages(messages)

        # ----------------------------------
        # Call OpenAI LLM
        # ----------------------------------

        if not marvin.settings.anthropic.api_key:
            raise ValueError(
                "Anthropic API key not found in settings. Please set it or use the"
                " MARVIN_ANTHROPIC_API_KEY environment variable."
            )

        client = anthropic.AsyncAnthropic(
            api_key=marvin.settings.anthropic.api_key.get_secret_value(),
            timeout=marvin.settings.llm_request_timeout_seconds,
        )

        kwargs.setdefault("temperature", self.temperature)
        kwargs.setdefault("max_tokens_to_sample", self.max_tokens)

        response = await client.completions.create(
            model=self.model,
            prompt=prompt,
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

Your have access to the following functions. Each has a name (which must be part
of your response), a description (which you should use to decide to call the
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
"""
