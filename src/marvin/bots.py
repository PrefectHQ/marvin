import json
import logging

from langchain.chat_models import ChatOpenAI
from langchain.schema import AIMessage, HumanMessage, SystemMessage
from pydantic import Field, PrivateAttr, validator

import marvin
from marvin.history import History, InMemoryHistory
from marvin.models.messages import Message
from marvin.plugins.base import Plugin
from marvin.utilities.types import MarvinBaseModel


class Bot(MarvinBaseModel):
    name: str = "Marvin"
    personality: str = "A helpful AI assistant that is clever, witty, and fun."
    instructions: str = "Provide clear, detailed, and helpful responses to users."

    plugins: list[Plugin.as_discriminated_union()] = Field(default_factory=list)
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

        messages = bot_instructions + plugin_instructions + history + [user_message]

        self.logger.debug_kv("User message", user_message.content, "bold blue")
        await self.history.add_message(user_message)

        finished = False

        while not finished:
            response = await self._say(messages=messages)
            ai_response = Message(role="ai", content=response)
            messages.append(ai_response)

            if response.startswith("marvin::plugin"):
                self.logger.debug_kv("Plugin Input", response, "bold blue")
                plugin_input = json.loads(response.split("marvin::plugin")[1])
                plugin_output = await self._run_plugin(
                    plugin_name=plugin_input["name"],
                    plugin_inputs=plugin_input["inputs"],
                )
                self.logger.debug_kv("Plugin output", plugin_output, "bold blue")
                plugin_message = Message(
                    role="system", content=f"Plugin Output: {plugin_output}"
                )
                messages.append(plugin_message)
            else:
                finished = True

        await self.history.add_message(ai_response)
        self.logger.debug_kv("AI message", response, "bold green")

        return response

    async def _run_plugin(self, plugin_name: str, plugin_inputs: dict) -> str:
        plugin = next((p for p in self.plugins if p.name == plugin_name), None)
        if plugin is None:
            raise ValueError(f"Plugin '{plugin_name}' not found.")

        return await plugin.run(**plugin_inputs)

    async def _get_bot_instructions(self) -> list[Message]:
        msg = Message(
            role="system",
            content=(
                f'Your name is "{self.name}" and'
                f' your personality is: {self.personality}. Your instructions are:'
                f' "{self.instructions}". Your responses must always reflect your'
                " personality."
            ),
        )
        return [msg]

    async def _get_plugin_instructions(self) -> list[Message]:
        plugin_instructions = Message(
            role="system",
            content=(
                "You have access to some plugins to assist you. To use a"
                " plugin, respond only with a JSON object that contains the plugin"
                " name and arguments. The plugin's output will be returned to you. For"
                " example, to use a plugin called `abc` with signature `(x: str,"
                " n_results: int = 10)`, respond with: "
                r'`marvin::plugin {"name": "abc", "inputs": {"x":'
                r' "hello"}}`'
                "The plugins you have access to are:"
            ),
        )
        plugins = [
            Message(role="system", content=p.get_instructions()) for p in self.plugins
        ]

        if plugins:
            return [plugin_instructions] + plugins
        return []

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
