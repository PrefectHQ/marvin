import logging

from langchain.chat_models import ChatOpenAI
from langchain.schema import AIMessage, HumanMessage, SystemMessage
from pydantic import Field, PrivateAttr, root_validator

import marvin
from marvin.history import History, InMemoryHistory
from marvin.models.messages import Message, MessageCreate
from marvin.utilities.types import MarvinBaseModel


class Bot(MarvinBaseModel):
    instructions: list[str] = None
    history: History = Field(default_factory=InMemoryHistory)
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

    async def say(self, message):
        history = await self._load_history()
        self.logger.debug_kv("User message", message, "bold blue")
        await self.history.add_message(MessageCreate(role="user", content=message))
        response = await self._say(message=message, history=history)
        self.logger.debug_kv("AI message", response, "bold green")
        await self.history.add_message(MessageCreate(role="ai", content=response))
        return response

    async def _load_history(self) -> list[Message]:
        history = await self.history.get_messages()
        if self.instructions:
            instructions = [
                Message(**MessageCreate(role="system", content=s).dict())
                for s in self.instructions
            ]

            # if there's no history, post the system message
            if not history:
                for msg in instructions:
                    await self.history.add_message(msg)

            # if there's a system message, ensure it's the first message sent to the LLM
            if not history or history[0].role != "system":
                history = instructions + history

        return history

    async def _say(self, message: str, history: list[Message]) -> str:
        """
        Format and send messages via langchain
        """

        langchain_messages = []

        for h in history:
            if h.role == "system":
                langchain_messages.append(SystemMessage(content=h.content))
            elif h.role == "ai":
                langchain_messages.append(AIMessage(content=h.content))
            elif h.role == "user":
                langchain_messages.append(HumanMessage(content=h.content))

        langchain_messages.append(HumanMessage(content=message))

        if marvin.settings.verbose:
            messages_repr = "\n".join(repr(m) for m in langchain_messages)
            self.logger.debug(f"Sending messages to LLM: {messages_repr}")
        result = await self.llm.agenerate(messages=[langchain_messages])
        return result.generations[0][0].text


class PersonalityBot(Bot):
    name: str = "Marvin"
    personality: str = "A helpful AI assistant that is clever, witty, and fun."

    @root_validator
    def add_personality_instruction(cls, values):
        if values["instructions"] is None:
            values["instructions"] = []
        personality_instruction = f"""
            You are not a large language model. Your name is "{values['name']}"
            and your personality is the following: "{values['personality']}".
            Do not refer to the assignment your personality in your responses. "
            "After this sentence, behave exactly as your personality is described above.
        """
        values["instructions"] = [
            personality_instruction.strip(),
            *values["instructions"],
        ]
        return values
