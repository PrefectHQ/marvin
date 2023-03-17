import inspect
import json
import logging
import re

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
DEFAULT_INSTRUCTIONS = inspect.cleandoc(
    """
    Respond to the user. Use plugins whenever you need additional information.
    """
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
    history: History.as_discriminated_union() = None
    llm: ChatOpenAI = Field(
        default_factory=lambda: ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.8),
        repr=False,
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
        plugin_instructions = await self._get_plugin_instructions()
        history = await self._get_history()
        user_message = Message(role="user", content=message)

        messages = [bot_instructions, plugin_instructions] + history + [user_message]

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

            # run plugins
            all_plugin_names = "|".join(p.name for p in self.plugins)
            plugin_regex = re.compile(f"({all_plugin_names})\[({{.*}})\]", re.DOTALL)
            matches = re.findall(plugin_regex, response)
            for plugin_name, plugin_inputs in matches:
                plugin_name, plugin_inputs = matches[0]
                try:
                    plugin_inputs = json.loads(plugin_inputs)
                    self.logger.debug_kv(
                        "Plugin input",
                        f"{plugin_name}: {plugin_inputs})",
                        "bold blue",
                    )
                    plugin_output = await self._run_plugin(
                        plugin_name=plugin_name,
                        plugin_inputs=plugin_inputs,
                    )
                    self.logger.debug_kv("Plugin output", plugin_output, "bold blue")

                    messages.append(
                        Message(
                            role="system", content=f"# Plugin request\n\n{response}"
                        )
                    )
                    messages.append(
                        Message(
                            role="system",
                            name="plugin",
                            content=f"# Plugin output\n\n{plugin_output}",
                        ),
                    )
                    messages.append(
                        Message(
                            role="system",
                            content="Remember to answer according to your personality!",
                        )
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

            if not matches:
                finished = True
                ai_message = Message(role="ai", content=response)
                messages.append(ai_message)
                await self.history.add_message(ai_message)

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
            Today is {pendulum.now().format("dddd, MMMM D, YYYY")}.
            Your name is {self.name} and your personality is
            "{self.personality}". 
            
            {self.instructions}
            """
        )

        return Message(role="system", content=bot_instructions)

    async def _get_plugin_instructions(self) -> Message:
        if self.plugins:
            plugin_descriptions = "\n\n".join(
                [p.get_full_description() for p in self.plugins]
            )

            plugin_names = ", ".join([p.name for p in self.plugins])
            plugin_overview = inspect.cleandoc(
                """
                You have access to plugins that can enhance your knowledge and
                capabilities in order to respond to the user. To use a plugin,
                you must use the following format
        
                ``` 
                [describe a step by step plan for using plugins to generate a
                response. Break down the question into discrete parts.]
                <plugin name>[{{<json plugin payload>}}]
                ``` 
                
                For example, if `Google` was an available plugin:
                
                ```
                Google[{{"query": "what is the largest city in the world?"}}]
                ```
                
                The system will respond with the plugin output.

                You only have access to the following plugins:
                
                {plugin_descriptions}
                """
            ).format(plugin_names=plugin_names, plugin_descriptions=plugin_descriptions)

            return Message(role="system", content=plugin_overview)

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
            else:
                raise ValueError(f"Unrecognized role: {msg.role}")

        if marvin.settings.verbose:
            messages_repr = "\n".join(repr(m) for m in langchain_messages)
            self.logger.debug(f"Sending messages to LLM: {messages_repr}")
        result = await self.llm.agenerate(
            messages=[langchain_messages], stop=["Plugin output:", "Plugin Output:"]
        )
        return result.generations[0][0].text
