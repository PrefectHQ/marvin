from langchain.chat_models import ChatOpenAI
from langchain.schema import AIMessage, HumanMessage, SystemMessage
from pydantic import Field

from marvin.memory import InMemory, Memory
from marvin.models.messages import Message, MessageCreate
from marvin.utilities.types import MarvinBaseModel


class Bot(MarvinBaseModel):
    system_messages: list[str] = None
    memory: Memory = Field(default_factory=InMemory)
    llm: ChatOpenAI = Field(default_factory=lambda: ChatOpenAI(temperature=0.9))

    async def say(self, message):
        history = await self._load_history()
        await self.memory.add_message(MessageCreate(role="user", content=message))
        response = await self._say(message=message, history=history)
        await self.memory.add_message(MessageCreate(role="ai", content=response))
        return response

    async def _load_history(self) -> list[Message]:
        history = await self.memory.get_messages()
        if self.system_messages:
            system_messages = [
                Message(**MessageCreate(role="system", content=s).dict())
                for s in self.system_messages
            ]

            # if there's no history, post the system message
            if not history:
                for msg in system_messages:
                    await self.memory.add_message(msg)

            # if there's a system message, ensure it's the first message sent to the LLM
            if not history or history[0].role != "system":
                history = system_messages + history

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

        result = await self.llm.agenerate(messages=[langchain_messages])
        return result.generations[0][0].text


class PersonalityBot(Bot):
    name: str
    personality: str
