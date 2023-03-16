import inspect
import json
import logging

import pendulum
from langchain.chat_models import ChatOpenAI
from langchain.schema import AIMessage, HumanMessage, SystemMessage
from pydantic import Field, PrivateAttr, validator

import marvin
from marvin.history import History, InMemoryHistory
from marvin.models.messages import Message
from marvin.plugins import Plugin
from marvin.utilities.types import MarvinBaseModel

DEFAULT_NAME = "Marvin"
DEFAULT_PERSONALITY = "A helpful assistant that is clever, witty, and fun."
DEFAULT_INSTRUCTIONS = (
    "You are not an 'AI assistant' or 'language model'. Instead, you are a human-like"
    " companion with a personality and opinions. You should provide clear, detailed,"
    " and helpful responses to users. Think step-by-step to solve questions with"
    " multiple parts. Do not return code unless requested. If you don't know an answer,"
    " say so."
)
DEFAULT_PLUGINS = [
    marvin.plugins.web.VisitURL(),
    marvin.plugins.duckduckgo.DuckDuckGo(),
    marvin.plugins.math.Calculator(),
]


class Bot(MarvinBaseModel):
    class Config:
        validate_assignment = True

    name: str = Field(None, description='The name of the bot. Defaults to "Marvin".')
    personality: str = Field(None, description="The bot's personality.")
    instructions: str = Field(
        None, description="Instructions for the bot to follow when responding."
    )
    plugins: list[Plugin.as_discriminated_union()] = Field(
        None, description="A list of plugins that the bot can use."
    )
    extend_plugins: list[Plugin.as_discriminated_union()] = Field(
        None,
        description=(
            "A list of plugins that the bot can use in addition to those provided as"
            " `plugins`. Useful for adding functionality without removing the default"
            " plugins."
        ),
    )
    history: History.as_discriminated_union() = None
    llm: ChatOpenAI = Field(
        default_factory=lambda: ChatOpenAI(temperature=0.9), repr=False
    )
    _logger: logging.Logger = PrivateAttr()

    def __init__(self, **data):
        super().__init__(**data)
        self._logger = marvin.get_logger(type(self).__name__)

    @property
    def logger(self):
        return self._logger

    @validator("name", always=True)
    def default_name(cls, v):
        if v is None:
            return DEFAULT_NAME
        return v

    @validator("personality", always=True)
    def default_personality(cls, v):
        if v is None:
            return DEFAULT_PERSONALITY
        return v

    @validator("instructions", always=True)
    def default_instructions(cls, v):
        if v is None:
            return DEFAULT_INSTRUCTIONS
        return v

    @validator("plugins", always=True)
    def default_plugins(cls, v):
        if v is None:
            return DEFAULT_PLUGINS
        return v

    @validator("history", always=True)
    def default_history(cls, v):
        if v is None:
            return InMemoryHistory()
        return v

    async def say(self, message):
        bot_instructions = await self._get_bot_instructions()
        history = await self._get_history()
        user_message = Message(role="user", content=message)

        messages = [bot_instructions] + history + [user_message]

        self.logger.debug_kv("User message", message, "bold blue")
        await self.history.add_message(user_message)

        finished = False
        counter = 0

        while not finished:
            counter += 1
            if counter > marvin.settings.bot_max_iterations:
                response = 'Error: "Max iterations reached. Please try again."'
            else:
                response = await self._say(messages=messages)
            ai_response = Message(role="ai", content=response)
            messages.append(ai_response)

            # run plugins if requested
            if "marvin::plugin" in response:
                self.logger.debug_kv("Plugin Input", response, "bold blue")
                try:
                    plugin_input = json.loads(response.split("marvin::plugin")[1])
                    plugin_output = await self._run_plugin(
                        plugin_name=plugin_input["name"],
                        plugin_inputs=plugin_input["inputs"],
                    )
                    self.logger.debug_kv("Plugin output", plugin_output, "bold blue")
                    messages.append(
                        Message(
                            role="ai",
                            name="plugin",
                            content=f"Plugin Output: {plugin_output}",
                        )
                    )
                except json.JSONDecodeError as exc:
                    messages.append(Message(role="system", content=f"Error: {exc}"))
            else:
                finished = True

        await self.history.add_message(ai_response)
        self.logger.debug_kv("AI message", response, "bold green")

        return response

    async def _run_plugin(self, plugin_name: str, plugin_inputs: dict) -> str:
        plugin = next((p for p in self.plugins if p.name == plugin_name), None)
        if plugin is None:
            return f'Plugin "{plugin_name}" not found.'
        try:
            plugin_output = plugin.run(**plugin_inputs)
            if inspect.iscoroutine(plugin_output):
                plugin_output = await plugin_output
            return plugin_output
        except Exception as exc:
            return f"Plugin encountered an error. Try again? Error message: {exc}"

    async def _get_bot_instructions(self) -> Message:
        bot_instructions = inspect.cleandoc(
            f"""
            # Overview
            Today is {pendulum.now().format("dddd, MMMM D, YYYY")}.
             
            # Personality
            
            You are "{self.name}". Your personality is "{self.personality}".
            You must always respond in a way that reflects your personality, 
            unless you decide to use a plug-in.
            
            # Instructions
            
            You must comply with the following instructions at all times.
            {self.instructions}
            """
        )

        if self.plugins:
            plugin_overview = inspect.cleandoc(
                """
                # Plugins 
                
                Plugins are a way to extend your functionality. To use one,
                start a response with "marvin::plugin" followed by a JSON
                document of the form {"name": <the plugin name>, "inputs":
                {<input name>: <input value>, ...}}. The plugin's output will be
                supplied to you in a new message so you can use it in your
                response to the user. Note the user will not see the plugin
                output.

                For example, to use a plugin named `abc` with signature `(x:
                str, n_results: int = 10) -> str` with `x="hello"`, you must
                respond with `marvin::plugin {"name": "abc", "inputs": {"x":
                "hello"}}`. 
                
                You have access to the following plugins:
                """
            )

            plugin_descriptions = "\n\n".join(
                [p.get_full_description() for p in self.plugins]
            )

            bot_instructions += f"\n\n{plugin_overview}\n\n{plugin_descriptions}"
            
        self.logger.debug_kv("System message", bot_instructions, "bold blue")
        return Message(role="system", content=bot_instructions)

    async def _get_history(self) -> list[Message]:
        return await self.history.get_messages()

    async def _say(self, messages: list[Message]) -> str:
        """
        Format and send messages via langchain
        """

        langchain_messages = []

        for msg in messages:
            if msg.role == "system":
                langchain_messages.append(SystemMessage(content=msg.content))
            elif msg.role == "ai":
                langchain_messages.append(AIMessage(content=msg.content))
            elif msg.role == "user":
                langchain_messages.append(HumanMessage(content=msg.content))

        if marvin.settings.verbose:
            messages_repr = "\n".join(repr(m) for m in langchain_messages)
            self.logger.debug(f"Sending messages to LLM: {messages_repr}")
        result = await self.llm.agenerate(messages=[langchain_messages])
        return result.generations[0][0].text
