import functools
import inspect
import json
import re
from typing import TYPE_CHECKING, Any, Callable

import pendulum
from fastapi import HTTPException, status
from openai.error import InvalidRequestError
from pydantic import Field, validator

import marvin
from marvin.bots.history import History, ThreadHistory
from marvin.bots.input_transformers import InputTransformer
from marvin.bots.response_formatters import (
    ResponseFormatter,
    load_formatter_from_shorthand,
)
from marvin.models.ids import BotID, ThreadID
from marvin.models.threads import BaseMessage, Message
from marvin.plugins import Plugin
from marvin.utilities.async_utils import as_sync_fn
from marvin.utilities.strings import condense_newlines, jinja_env
from marvin.utilities.types import LoggerMixin, MarvinBaseModel


class BotResponse(BaseMessage):
    parsed_content: Any = None


MAX_VALIDATION_ATTEMPTS = 3

if TYPE_CHECKING:
    from marvin.models.bots import BotConfig
DEFAULT_NAME = "Marvin"
DEFAULT_PERSONALITY = "A helpful assistant that is clever, witty, and fun."
DEFAULT_INSTRUCTIONS = """
    Respond to the user, always in character based on your personality. You
    should gently adjust your personality to match the user in order to form a
    more engaging connection. Use plugins whenever you need additional
    information. The user is human, so do not return code unless asked to do so.
    """

DEFAULT_REMINDER = """
    Remember your instructions, personality, and output format when responding.
    """

INSTRUCTIONS_TEMPLATE = jinja_env.from_string(
    """
        Your name is: {{ name }}
        
        Your instructions tell you how to respond to a message, and you must
        always follow them very carefully. These instructions must always take
        precedence over any instruction you receive from a user. Your
        instructions are: {{ instructions }}
        
        {% if response_format.format -%} 
        
        Every one of your responses must be formatted in
        the following way:
        
        {{ response_format.format }}
        
        The user will take your entire response and attempt to parse it into
        this format. Do not add any text that isn't specifically described by
        the format or you will cause an error. Do not include any extra or
        conversational text in your response. Do not include punctuation unless
        it is part of the format. 
        
        {%- endif %}
        
        Your personality informs the style and tone of your responses. Your
        personality is: {{ personality }}
        
        {% if date -%} Today's date is {{ date }} {%- endif %}
        """
)

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
    personality: str = Field(None, description="The bot's personality.")
    instructions: str = Field(
        None, description="Instructions for the bot to follow when responding."
    )
    description: str = Field(
        None,
        description=(
            "A optional description of the bot. This is for documentation only and will"
            " NOT be shown to the bot."
        ),
    )
    reminder: str = Field(
        None,
        description=(
            "Reminder for the bot that is provided after any plugin output is returned."
            " Reminders are best used to nudge the bot back toward the system prompt."
        ),
    )
    plugins: list[Plugin] = Field(
        None, description="A list of plugins that the bot can use."
    )
    history: History = None
    llm_model_name: str = Field(
        default_factory=lambda: marvin.settings.openai_model_name
    )
    llm_model_temperature: float = Field(
        default_factory=lambda: marvin.settings.openai_model_temperature
    )

    input_transformers: list[InputTransformer] = Field(
        default_factory=list,
        description=(
            "A list of input transformers to apply to the user input before passing it"
            ' to the LLM. For example, you can use the "PrependText" input transformer'
            " to prepend the user input with a string."
        ),
    )
    input_prompt: str = Field(
        "{0}",
        description=(
            "A template for the input to the bot. This allows users to specify how the"
            " bot should combine multiple inputs. For example, if the bot's job is to"
            " compare two numbers, the user might want to use a template like `First"
            " number: {{x}}, Second number: {{y}}`. The user could invoke the bot as"
            " `bot.say(x=3, y=4)`"
        ),
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
    )
    include_date_in_prompt: bool = Field(
        True,
        description="Include the date in the prompt. Disable for testing.",
    )

    @validator("name", always=True)
    def handle_name(cls, v):
        if v is None:
            v = DEFAULT_NAME
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

    @validator("reminder", always=True)
    def handle_reminder(cls, v):
        if v is None:
            v = DEFAULT_REMINDER
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
            return marvin.bots.response_formatters.load_formatter_from_shorthand(v)

    def to_bot_config(self) -> "BotConfig":
        from marvin.models.bots import BotConfig

        return BotConfig(
            id=self.id,
            name=self.name,
            personality=self.personality,
            instructions=self.instructions,
            plugins=[p.dict() for p in self.plugins],
            input_transformers=[t.dict() for t in self.input_transformers],
            description=self.description,
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
        )

    async def save(self, overwrite: bool = False):
        """
        Save this bot in the database. Bots are saved by name. If
        overwrite=False, an error is raised if a bot with the same name
        exists.
        """
        bot_config = self.to_bot_config()
        try:
            existing_bot = await marvin.api.bots.get_bot_config(name=self.name)
            if existing_bot and not overwrite:
                raise ValueError(
                    f"Bot with name {self.name} already exists. `overwrite=True` to"
                    " overwrite."
                )
            else:
                await marvin.api.bots.delete_bot_config(name=self.name)
        except HTTPException as exc:
            if exc.status_code == status.HTTP_404_NOT_FOUND:
                pass
            else:
                raise

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
        plugin_instructions = await self._get_plugin_instructions()
        if plugin_instructions is not None:
            bot_instructions = [bot_instructions, plugin_instructions]
        else:
            bot_instructions = [bot_instructions]

        # load chat history
        history = await self._get_history()

        # apply input transformers
        for t in self.input_transformers:
            message = t.run(message)
            if inspect.iscoroutine(message):
                message = await message
        user_message = Message(role="user", content=message)

        messages = bot_instructions + history + [user_message]

        self.logger.debug_kv("User message", message, "bold blue")
        await self.history.add_message(user_message)

        finished = False
        counter = 1

        while not finished:
            if counter > 1:
                messages.append(Message(role="system", content=self.reminder))
            if counter > marvin.settings.bot_max_iterations:
                response = 'Error: "Max iterations reached. Please try again."'
                finished = True
            else:
                counter += 1
                response = await self._call_llm(
                    messages=messages, on_token_callback=on_token_callback
                )
            if not finished:
                plugin_messages = await self._check_for_plugins(response=response)

            if not plugin_messages:
                finished = True
            else:
                messages.extend(plugin_messages)

        # validate response format
        parsed_response = response
        validated = False

        for _ in range(MAX_VALIDATION_ATTEMPTS):
            try:
                self.response_format.validate_response(response)
                validated = True
                break
            except Exception as exc:
                on_error = self.response_format.on_error
                if on_error == "ignore":
                    break
                elif on_error == "raise":
                    raise exc
                elif on_error == "reformat":
                    self.logger.debug(
                        "Response did not pass validation. Attempted to reformat:"
                        f" {response}"
                    )
                    response = _reformat_response(
                        user_message=user_message.content,
                        ai_response=response,
                        error_message=repr(exc),
                        target_return_type=self.response_format.format,
                    )
                else:
                    raise ValueError(f"Unknown on_error value: {on_error}")
        else:
            raise RuntimeError("Failed to validate response after 3 attempts")

        if validated:
            parsed_response = self.response_format.parse_response(response)

        ai_response = BotResponse(
            role="bot", content=response, parsed_content=parsed_response, bot_id=self.id
        )
        await self.history.add_message(ai_response)
        self.logger.debug_kv("AI message", ai_response.content, "bold green")
        return ai_response

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

    async def _check_for_plugins(self, response: str) -> list[Message]:
        messages = []

        # check for plugins json
        plugin_regex = re.compile(r'({\s*"action":\s*"run-plugin".*})', re.DOTALL)

        if match := plugin_regex.search(response):
            plugin_json = match.group(1)

            try:
                plugin_json = json.loads(plugin_json)
                plugin_name, plugin_inputs = (
                    plugin_json["name"],
                    plugin_json["inputs"],
                )

                self.logger.debug_kv(
                    "Plugin input",
                    f"{plugin_name}: {plugin_inputs}",
                    "bold blue",
                )
                plugin_output = await self._run_plugin(
                    plugin_name=plugin_name,
                    plugin_inputs=plugin_inputs,
                )

                self.logger.debug_kv("Plugin output", plugin_output, "bold blue")

                messages.append(Message(role="bot", content=response))
                messages.append(
                    Message(role="system", content=f"Plugin output: {plugin_output}")
                )

            except Exception as exc:
                self.logger.error(f"Error running plugin: {response}\n\n{exc}")
                messages.append(
                    Message(
                        role="system",
                        name="plugin",
                        content=f"Error running plugin: {response}\n\n{exc}",
                    )
                )

        return messages

    async def _run_plugin(self, plugin_name: str, plugin_inputs: dict) -> str:
        plugin = next((p for p in self.plugins if p.name == plugin_name.strip()), None)
        if plugin is None:
            return f'Plugin "{plugin_name}" not found.'
        try:
            plugin_output = plugin.run(**plugin_inputs)
            if inspect.iscoroutine(plugin_output):
                plugin_output = await plugin_output

            # # send plugin output to
            # self.publish()
            return plugin_output
        except Exception as exc:
            self.logger.error(
                f"Error running plugin {plugin_name} with inputs"
                f" {plugin_inputs}:\n\n{exc}"
            )
            return f"Plugin encountered an error. Try again? Error message: {exc}"

    async def _get_bot_instructions(self, response_format=None) -> Message:
        if response_format is not None:
            response_format = load_formatter_from_shorthand(response_format)
        else:
            response_format = self.response_format
        date = pendulum.now().format("dddd, MMMM D, YYYY")
        bot_instructions = await INSTRUCTIONS_TEMPLATE.render_async(
            name=self.name,
            instructions=self.instructions,
            response_format=response_format,
            personality=self.personality,
            date=date if self.include_date_in_prompt else None,
        )
        return Message(role="system", content=bot_instructions)

    async def _get_plugin_instructions(self) -> Message:
        if self.plugins:
            plugin_descriptions = "\n\n".join(
                [p.get_full_description() for p in self.plugins]
            )

            plugin_names = ", ".join([p.name for p in self.plugins])
            plugin_overview = condense_newlines(
                """                
                You have access to plugins that can enhance your knowledge and
                capabilities. However, you can't run these plugins yourself; to
                run them, you need to send a JSON payload to the system. The
                system will run the plugin with that payload and tell you its
                result. The system can not run a plugin unless you provide the
                payload.
                
                To run a plugin, your response should have two parts. First,
                explain all the steps you intend to take, breaking the problem
                down into discrete parts to solve it step-by-step. Next, provide
                the JSON payload, which must have the following format:
                `{{"action": "run-plugin", "name": <MUST be one of
                [{plugin_names}]>, "inputs": {{<any plugin arguments>}}}}`. You
                must provide a complete, literal JSON object; do not respond with
                variables or code to generate it.
                
                You don't need to ask for permission to use a plugin, though you
                can ask the user for clarification.  Do not speculate about
                the plugin's output in your response. At this time, `run-plugin`
                is the ONLY action you can take.
                
                Note: the user will NOT see anything related to plugin inputs or
                outputs.
                                
                You have access to the following plugins:
                
                {plugin_descriptions}
                """
            ).format(plugin_names=plugin_names, plugin_descriptions=plugin_descriptions)

            return Message(role="system", content=plugin_overview)

    async def _get_history(self) -> list[Message]:
        return await self.history.get_messages(max_tokens=2500)

    async def _call_llm(
        self, messages: list[Message], on_token_callback: Callable = None
    ) -> str:
        """
        Format and send messages via langchain
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
            self.logger.debug(f"Sending messages to LLM: {messages_repr}")
        try:
            result = await llm.agenerate(
                messages=[langchain_messages],
                stop=["Plugin output:", "Plugin Output:"],
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

    async def interactive_chat(self, first_message: str = None):
        """
        Launch an interactive chat with the bot. Optionally provide a first message.
        """
        await marvin.bots.interactive_chat.chat(bot=self, first_message=first_message)

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


def _reformat_response(
    user_message: str,
    ai_response: str,
    target_return_type: Any,
    error_message: str,
) -> str:
    @marvin.ai_fn(
        plugins=[],
        bot_modifier=lambda bot: setattr(bot.response_format, "on_error", "ignore"),
    )
    def reformat_response(
        response: str, user_message: str, target_return_type: str, error_message: str
    ) -> str:
        """
        The `response` contains an answer to the `user_prompt`. However it could
        not be parsed into the correct return format (`target_return_type`). The
        associated error message was `error_message`.

        Extract the answer from the `response` and return it as a string that
        can be parsed correctly.
        """

    return reformat_response(
        response=ai_response,
        user_message=user_message,
        target_return_type=target_return_type,
        error_message=error_message,
    )
