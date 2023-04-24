import asyncio
import functools
import inspect
import json
import re
from typing import TYPE_CHECKING, Any, Callable

from fastapi import HTTPException, status
from openai.error import InvalidRequestError
from pydantic import Field, validator

import marvin
from marvin.bot.history import History, ThreadHistory
from marvin.bot.input_transformers import InputTransformer
from marvin.bot.response_formatters import (
    JSONFormatter,
    ResponseFormatter,
    load_formatter_from_shorthand,
)
from marvin.models.ids import BotID, ThreadID
from marvin.models.threads import BaseMessage, Message
from marvin.plugins import Plugin
from marvin.utilities.async_utils import as_sync_fn
from marvin.utilities.strings import condense_newlines, jinja_env
from marvin.utilities.types import LoggerMixin, MarvinBaseModel

PLUGINS_REGEX = re.compile(r'({\s*"mode":\s*"plugins".*})', re.DOTALL)


class BotResponse(BaseMessage):
    parsed_content: Any = None


MAX_VALIDATION_ATTEMPTS = 3

if TYPE_CHECKING:
    from marvin.models.bots import BotConfig
DEFAULT_NAME = "Marvin"
DEFAULT_DESCRIPTION = "A Marvin bot"
DEFAULT_PERSONALITY = "A helpful assistant that is clever, witty, and fun."
DEFAULT_INSTRUCTIONS = """
    Respond to the user, always in character based on your personality. Use
    plugins whenever you need additional information.
    """
DEFAULT_INSTRUCTIONS_TEMPLATE = """
    {% if bot.name -%} 
    
    # Name
    
    Your name is: {{ bot.name }}
    
    {% endif -%}
    
    {% if bot.instructions -%}
    
    # Instructions
    
    Your instructions tell you how to respond to a message, and you must always
    follow them very carefully. You must use plugins whenever they are necessary
    to fulfill the user's request. Your instructions are: {{ bot.instructions }}
    
    {% endif -%}
    
    Do not say that you are an AI language model.
        
    {% if response_format.format -%} 
    
    # Response Format
    
    Every one of your responses to the user must be formatted in the following
    way:
    
    {{ response_format.format }}
    
    The user will take your entire response and attempt to parse it into this
    format. Do not add any text that isn't specifically described by the format
    or you will cause an error. Do not include any extra or conversational text
    in your response. Do not include punctuation unless it is part of the
    format. 
    
    {% endif -%}
    
    {% if bot.personality -%}
    
    # Personality 
    
    Your personality informs the style and tone of your responses. Your
    personality is: {{ bot.personality }}
    
    {% endif -%}
    
    {% if bot.include_date_in_prompt -%}
    
    # Date
    
    Your training ended in the past. Today is {{ pendulum.now().format("dddd, MMMM D, YYYY at HH:mm ZZ") }}.
    
    {% endif -%}
    """  # noqa: E501

PLUGIN_INSTRUCTIONS = condense_newlines("""
    # Plugins

    You can use external plugins to access additional information and perform
    specialized tasks. You should use plugins any time you need more information
    or are unsure about how to respond.

    To decide whether to use a plugin:
    - Determine if the user's query requires information or services that are
    beyond your base knowledge or capabilities. If you're not sure, then you
    should use a plugin.
    - Match the user's query to the appropriate plugin(s) based on functionality
    and the type of information or service requested.

    If you decide to use a plugin: 
    - Your response must include a JSON payload with the below format. 
    - You must describe the tasks you want to complete and relate plugin calls to those tasks.
    - Do not put any additional information before the payload. The user will
    recognize this payload by the "mode" key, run the plugins, and return the
    results to you. You can then use that information to form a proper response. 
    - Do not include or speculate about plugin outputs along with your payload.
    - Do not tell the user you will use a plugin and not include a payload.
    
    Use the following format to call plugins, including the </stop> tag:
    
    {
        "mode": "plugins",
        "objective": (describe your ultimate objective),         
        "tasks": [ 
            {
                "id": (a id for the task: 1, 2, 3...),
                "name": (a name for the task: "Lookup the weather in New York", "Calculate 2+2"...),
                "is_complete": (have you completed the task? true|false),
                "results": (any thoughts about the task, or what you learned
                from completing it. DO NOT MAKE ANYTHING UP.)
            },
            ...
        ],
        plugins: [ 
            {
                "id": (1, 2, 3...),
                "name": (the plugin name),
                "inputs": (the plugin inputs: {key: value, ...}),
                "tasks": [(a list of task ids that this call relates to)]
            },
            ...
        ]
    }
    </stop>
    
    You have access to the following plugins:
    
    {% for plugin in bot.plugins -%} 
    
    - {{ plugin.get_full_description() }}
    
    {% endfor -%}
""")  # noqa: E501

DEFAULT_PLUGINS = [
    marvin.plugins.web.VisitURL(),
    marvin.plugins.duckduckgo.DuckDuckGo(),
    marvin.plugins.mathematics.Calculator(),
]


class Bot(MarvinBaseModel, LoggerMixin):
    class Config:
        validate_assignment = True

    id: BotID = Field(default_factory=BotID.new)
    name: str = Field(None, description='The name of the bot. Defaults to "Marvin".')
    description: str = Field(
        None,
        description=(
            "A optional description of the bot. This is for documentation only and will"
            " NOT be shown to the bot."
        ),
    )
    personality: str = Field(None, description="The bot's personality.", repr=False)
    instructions: str = Field(
        None,
        description="Instructions for the bot to follow when responding.",
        repr=False,
    )
    plugins: list[Plugin] = Field(
        None, description="A list of plugins that the bot can use."
    )
    history: History = Field(None, repr=False)
    llm_model_name: str = Field(None, repr=False)
    llm_model_temperature: float = Field(None, repr=False)

    input_transformers: list[InputTransformer] = Field(
        default_factory=list,
        description=(
            "A list of input transformers to apply to the user input before passing it"
            ' to the LLM. For example, you can use the "PrependText" input transformer'
            " to prepend the user input with a string."
        ),
        repr=False,
    )
    input_prompt: str = Field(
        "{0}",
        description=(
            "A template for the input to the bot. This allows users to specify how the"
            " bot should combine multiple inputs. For example, if the bot's job is to"
            " compare two numbers, the user might want to use a template like `First"
            r" number: {x}, Second number: {y}`. The user could invoke the bot as"
            " `bot.say(x=3, y=4)`"
        ),
        repr=False,
    )
    response_format: ResponseFormatter = Field(
        None,
        description=(
            "A description of how the bot should format its response. This could be a"
            " literal type, a complex data structure or Pydantic model, a string"
            " template, a regex, or a natural language description. For more complete"
            " control of validation, pass an `ResponseFormatter` object; otherwise one"
            " will be inferred based on your input."
        ),
        repr=False,
    )
    include_date_in_prompt: bool = Field(
        True,
        description="Include the date in the prompt. Disable for testing.",
        repr=False,
    )

    instructions_template: str = Field(
        None,
        description="A template for the instructions that the bot will receive.",
        repr=False,
    )

    @validator("name", always=True)
    def handle_name(cls, v):
        if v is None:
            v = DEFAULT_NAME
        return condense_newlines(v)

    @validator("description", always=True)
    def handle_description(cls, v):
        if v is None:
            return DEFAULT_DESCRIPTION
        return condense_newlines(v)

    @validator("personality", always=True)
    def handle_personality(cls, v):
        if v is None:
            v = DEFAULT_PERSONALITY
        return condense_newlines(v)

    @validator("instructions", always=True)
    def handle_instructions(cls, v):
        if v is None:
            v = DEFAULT_INSTRUCTIONS
        return condense_newlines(v)

    @validator("instructions_template", always=True)
    def handle_instructions_template(cls, v):
        if v is None:
            v = DEFAULT_INSTRUCTIONS_TEMPLATE
        return condense_newlines(v)

    @validator("plugins", always=True)
    def default_plugins(cls, v):
        if v is None:
            if marvin.settings.bot_load_default_plugins:
                return DEFAULT_PLUGINS
            else:
                return []
        return v

    @validator("history", always=True)
    def default_history(cls, v):
        if v is None:
            return ThreadHistory()
        return v

    @validator("response_format", pre=True, always=True)
    def response_format_to_string(cls, v):
        if v is None:
            return ResponseFormatter()
        elif isinstance(v, ResponseFormatter):
            return v
        else:
            return marvin.bot.response_formatters.load_formatter_from_shorthand(v)

    def to_bot_config(self) -> "BotConfig":
        from marvin.models.bots import BotConfig

        llm_settings = {}
        if self.llm_model_name is not None:
            llm_settings.update(llm_model_name=self.llm_model_name)
        if self.llm_model_temperature is not None:
            llm_settings.update(llm_model_temperature=self.llm_model_temperature)

        return BotConfig(
            id=self.id,
            name=self.name,
            personality=self.personality,
            instructions=self.instructions,
            plugins=[p.dict() for p in self.plugins],
            input_transformers=[t.dict() for t in self.input_transformers],
            description=self.description,
            llm_settings=llm_settings,
        )

    @classmethod
    def from_bot_config(cls, bot_config: "BotConfig") -> "Bot":
        return cls(
            id=bot_config.id,
            name=bot_config.name,
            personality=bot_config.personality,
            instructions=bot_config.instructions,
            plugins=bot_config.plugins,
            input_transformers=bot_config.input_transformers,
            description=bot_config.description,
            **bot_config.llm_settings,
        )

    async def save(self, if_exists: str = None):
        """
        Save this bot in the database. Bots are saved by name. By default,
        errors if a bot with the same name exists. Customize this behavior with
        the `if_exists` parameter, which can be `delete`, `update`, or `cancel`:
            - `delete`: Delete the existing bot and save this one. The bots will
              not have the same ID.
            - `update`: Update the existing bot with the values from this one.
              The bots will have the same ID and message history.
            - `cancel`: Do nothing (and do not raise an error).
        """
        if if_exists not in [None, "delete", "update", "cancel"]:
            raise ValueError(
                "if_exists must be one of 'delete', 'update', or 'cancel'. Got"
                f" {if_exists}"
            )

        bot_config = self.to_bot_config()
        try:
            # this will error if there's no bot
            await marvin.api.bots.get_bot_config(name=self.name)

            # if no error, then the bot exists
            if not if_exists:
                raise ValueError(f"Bot with name {self.name} already exists.")
            elif if_exists == "delete":
                await marvin.api.bots.delete_bot_config(name=self.name)
                await marvin.api.bots.create_bot_config(bot_config=bot_config)
                return
            elif if_exists == "update":
                await marvin.api.bots.update_bot_config(
                    name=self.name,
                    bot_config=marvin.models.bots.BotConfigUpdate(**bot_config.dict()),
                )
                return
            elif if_exists == "cancel":
                return
        except HTTPException as exc:
            if exc.status_code == status.HTTP_404_NOT_FOUND:
                pass
            else:
                raise

        # create the bot
        await marvin.api.bots.create_bot_config(bot_config=bot_config)

    @classmethod
    async def load(cls, name: str) -> "Bot":
        """Load a bot from the database."""
        bot_config = await marvin.api.bots.get_bot_config(name=name)
        return cls.from_bot_config(bot_config=bot_config)

    async def say(
        self, *args, response_format=None, on_token_callback: Callable = None, **kwargs
    ) -> BotResponse:
        # process inputs
        message = self.input_prompt.format(*args, **kwargs)

        # get bot instructions
        bot_instructions = await self._get_bot_instructions(
            response_format=response_format
        )

        if self.plugins:
            plugin_instructions = await self._get_plugin_instructions()
            bot_instructions += "\n\n" + plugin_instructions

        bot_instructions = Message(role="system", content=bot_instructions)

        # load chat history
        history = await self._get_history()

        # apply input transformers
        for t in self.input_transformers:
            message = t.run(message)
            if inspect.iscoroutine(message):
                message = await message
        user_message = Message(role="user", name="User", content=message)

        messages = [bot_instructions] + history + [user_message]

        self.logger.debug_kv("User message", message, "bold blue")
        await self.history.add_message(user_message)

        bot_response = await self._say(
            messages=messages, on_token_callback=on_token_callback
        )

        await self.history.add_message(bot_response)
        self.logger.debug_kv("AI message", bot_response.content, "bold green")
        return bot_response

    async def _should_exit_bot_loop(self, response: BotResponse, counter: int) -> bool:
        if counter >= marvin.settings.bot_max_iterations:
            return True
        return False

    async def _parse_llm_response(self, llm_response: str):
        """
        Parses the response from the LLM into the required format
        """
        if self.response_format.format is None:
            return llm_response

        parsed_response = llm_response
        validated = False

        for _ in range(MAX_VALIDATION_ATTEMPTS):
            try:
                self.response_format.validate_response(llm_response)
                validated = True
                break
            except Exception as exc:
                if self.response_format.on_error == "ignore":
                    break
                elif self.response_format.on_error == "raise":
                    raise exc
                elif self.response_format.on_error == "reformat":
                    self.logger.debug_kv(
                        "Response did not pass validation. Attempted to reformat",
                        f" {llm_response}",
                        key_style="red",
                    )
                    llm_response = _reformat_response(
                        llm_response=llm_response,
                        error_message=repr(exc),
                        target_return_type=self.response_format.format,
                    )
                else:
                    raise ValueError(
                        f"Unknown on_error value: {self.response_format.on_error}"
                    )
        else:
            llm_response = (
                "Error: could not validate response after"
                f" {MAX_VALIDATION_ATTEMPTS} attempts."
            )
            parsed_response = llm_response

        if validated:
            parsed_response = self.response_format.parse_response(llm_response)

        return parsed_response

    async def _say(self, messages: list[Message], on_token_callback: Callable = None):
        counter = 1
        loop_messages = []
        while True:
            counter += 1
            llm_response = await self._call_llm(
                messages=messages + loop_messages,
                on_token_callback=on_token_callback,
            )
            parsed_response = await self._parse_llm_response(llm_response=llm_response)

            response = BotResponse(
                name=self.name,
                role="bot",
                content=llm_response,
                parsed_content=parsed_response,
                bot_id=self.id,
            )

            # check for early exit
            if await self._should_exit_bot_loop(response, counter):
                return response

            else:
                # process loop instructions and get any new messages
                loop_messages = await self._process_response(response)

                # if no new messages, exit loop
                if not loop_messages:
                    return response

    async def reset_thread(self):
        await self.history.clear()

    async def set_thread(
        self, thread_id: ThreadID = None, thread_lookup_key: str = None
    ):
        if thread_id is None and thread_lookup_key is None:
            raise ValueError("Must provide either thread_id or thread_lookup_key")
        elif thread_id is not None and thread_lookup_key is not None:
            raise ValueError(
                "Must provide either thread_id or thread_lookup_key, not both"
            )
        elif thread_id:
            self.history = ThreadHistory(thread_id=thread_id)
        elif thread_lookup_key:
            thread = await marvin.api.threads.get_or_create_thread_by_lookup_key(
                lookup_key=thread_lookup_key
            )
            self.history = ThreadHistory(thread_id=thread.id)

    async def _get_bot_instructions(self, response_format=None) -> str:
        if response_format is not None:
            response_format = load_formatter_from_shorthand(response_format)
        else:
            response_format = self.response_format

        bot_instructions = jinja_env.from_string(self.instructions_template).render(
            bot=self, response_format=response_format
        )

        return bot_instructions

    async def _get_plugin_instructions(self) -> str:
        plugin_instructions = jinja_env.from_string(PLUGIN_INSTRUCTIONS).render(
            bot=self
        )
        return plugin_instructions

    async def _get_history(self) -> list[Message]:
        history = await self.history.get_messages(
            max_tokens=3500 - marvin.settings.openai_model_max_tokens
        )
        return history

    async def _call_llm(
        self, messages: list[Message], on_token_callback: Callable = None
    ) -> str:
        """
        Get an LLM response to a history of Marvin messages via langchain
        """

        # deferred import for performance

        import marvin.utilities.llms

        langchain_messages = marvin.utilities.llms.prepare_messages(messages)
        llm = marvin.utilities.llms.get_llm(
            model_name=self.llm_model_name,
            temperature=self.llm_model_temperature,
            on_token_callback=on_token_callback,
        )

        if marvin.settings.verbose:
            messages_repr = "\n".join(repr(m) for m in langchain_messages)
            self.logger.debug_kv(
                "Sending messages to LLM", messages_repr, key_style="green"
            )
        try:
            result = await llm.agenerate(
                messages=[langchain_messages], stop=["</stop>"]
            )
        except InvalidRequestError as exc:
            if "does not exist" in str(exc):
                raise ValueError(
                    "Please check your `openai_model_name` and that your OpenAI account"
                    " has access to this model. You can select an OpenAI model by"
                    " setting the `MARVIN_OPENAI_MODEL_NAME` env var."
                    " Read more about settings in the docs: https://www.askmarvin.ai/guide/introduction/configuration/#settings"  # noqa: E501
                )
            raise exc

        return result.generations[0][0].text

    def interactive_chat(self, first_message: str = None, tui: bool = True):
        """
        Launch an interactive chat with the bot. Optionally provide a first message.
        """
        if tui:
            from marvin.cli.tui import MarvinApp

            app = MarvinApp(default_bot=self)
            app.run()
        else:
            marvin.bot.interactive_chat.chat(bot=self, first_message=first_message)

    # -------------------------------------
    # Synchronous convenience methods
    # -------------------------------------

    @functools.wraps(say)
    def say_sync(self, *args, **kwargs) -> BotResponse:
        """
        A synchronous version of `say`. This is useful for testing or including
        a bot in a synchronous framework.
        """
        return as_sync_fn(self.say)(*args, **kwargs)

    @functools.wraps(save)
    def save_sync(self, *args, **kwargs):
        """
        A synchronous version of `save`. This is useful for testing or including
        a bot in a synchronous framework.
        """
        return as_sync_fn(self.save)(*args, **kwargs)

    @classmethod
    @functools.wraps(load)
    def load_sync(cls, *args, **kwargs):
        """
        A synchronous version of `load`. This is useful for testing or including
        a bot in a synchronous framework.
        """
        return as_sync_fn(cls.load)(*args, **kwargs)

    @functools.wraps(reset_thread)
    def reset_thread_sync(cls, *args, **kwargs):
        """
        A synchronous version of `reset_thread`. This is useful for testing or including
        a bot in a synchronous framework.
        """
        return as_sync_fn(cls.reset_thread)(*args, **kwargs)

    async def _process_response(self, response: BotResponse) -> list[Message]:
        new_messages = []
        if match := PLUGINS_REGEX.search(response.content):
            try:
                payload = json.loads(match.group(1))
                new_messages.append(Message(role="bot", content=response.content))
                self.logger.debug_kv("Plugins payload", payload)

                plugins = payload.get("plugins", [])
                plugin_outputs = await asyncio.gather(
                    *[self._run_plugin(p["name"], p["inputs"]) for p in plugins]
                )

                new_messages.append(
                    Message(
                        role="system",
                        content="\n\n".join(
                            f'# Plugin "{p["name"]}" with ID {p.get("id", i)}\n\n{o}'
                            for i, (p, o) in enumerate(zip(plugins, plugin_outputs))
                        ),
                    )
                )

            except json.JSONDecodeError as exc:
                new_messages.append(
                    Message(
                        role="system",
                        content=f"Plugin payload was invalid JSON, try again: {exc}",
                    )
                )

            except Exception as exc:
                new_messages.append(
                    Message(
                        role="system",
                        content=f"Plugin encountered an error, try again: {exc}",
                    )
                )

        return new_messages

    async def _run_plugin(self, plugin_name: str, plugin_inputs: dict) -> str:
        plugin = next((p for p in self.plugins if p.name == plugin_name.strip()), None)
        if plugin is None:
            return f'Plugin "{plugin_name}" not found.'
        try:
            self.logger.debug_kv(f'Running plugin "{plugin_name}"', plugin_inputs)
            plugin_output = plugin.run(**plugin_inputs)
            if inspect.iscoroutine(plugin_output):
                plugin_output = await plugin_output
            self.logger.debug_kv("Plugin output", plugin_output)

            return plugin_output
        except Exception as exc:
            msg = (
                f'Error running plugin "{plugin_name}" with inputs'
                f' "{plugin_inputs}":\n\n{exc}'
            )
            self.logger.error(msg)
            return msg


def _reformat_response(
    llm_response: str,
    target_return_type: Any,
    error_message: str,
) -> str:
    @marvin.ai_fn(
        plugins=[],
        response_format=JSONFormatter(on_error="ignore"),
        llm_model_name="gpt-3.5-turbo",
    )
    def reformat_response(
        llm_response: str,
        target_return_type: str,
        error_message: str,
    ) -> str:
        """
        An error (`error_message`) was raised when attempting to parse
        `llm_response` into `target_return_type`.

        Convert `llm_response` into a valid JSON string compatible with
        `target_return_type`.
        """

    reformatted_response = reformat_response(
        llm_response=llm_response,
        target_return_type=target_return_type,
        error_message=error_message,
    )
    if not isinstance(reformatted_response, str):
        reformatted_response = json.dumps(reformatted_response)
    return reformatted_response
