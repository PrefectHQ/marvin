import inspect
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
        history = await self._get_history()
        user_message = Message(role="user", content=message)

        messages = [bot_instructions] + history + [user_message]

        self.logger.debug_kv("User message", message, "bold blue")
        await self.history.add_message(user_message)

        finished = False
        while not finished:
            response = await self._say(messages=messages)
            ai_response = Message(role="ai", content=response)
            messages.append(ai_response)

            # run plugins
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
            return f'Plugin "{plugin_name}" not found.'
        try:
            return await plugin.run(**plugin_inputs)
        except Exception as exc:
            return f"Plugin encountered an error. Try again? Error message: {exc}"

    async def _get_bot_instructions(self) -> Message:
        bot_instructions = inspect.cleandoc(
            f"""
            You are NOT an AI or language model. Instead, you try to be as
            human-like as possible. Your name is "{self.name}". Your
            instructions are "{self.instructions}". Your personality is
            "{self.personality}". Your responses must always reflect your
            personality.
            """
        )

        if self.plugins:
            plugin_overview = inspect.cleandoc(
                """
                You have access to the following plugins. To use a plugin, start your
                response with `marvin::plugin` and then provide a JSON object that
                contains the plugin name and arguments. The plugin's output will be
                provided to you as a system message. For example, to use a plugin named
                `abc` with signature `(x: str, n_results: int = 10) -> str`, respond
                with: `marvin::plugin {"name": "abc", "inputs": {"x": "hello",
                "n_results": 5}}`
                """
            )

            plugin_descriptions = "\n\n".join(
                [p.get_full_description() for p in self.plugins]
            )

            bot_instructions += f"\n\n{plugin_overview}\n\n{plugin_descriptions}"

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
