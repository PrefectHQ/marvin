from typing import Callable, List

from marvin.engines.language_models import ChatLLM, OpenAIFunction
from marvin.models.messages import Message
from pydantic import BaseModel, Field


class Flow(BaseModel):
    pass


class OpenAIFlow(Flow):
    stop: bool = False
    function_list: List[Callable] = Field(default=[], alias="functions")
    engine: ChatLLM = ChatLLM()

    async def functions(self, as_dict: bool = False, as_model: bool = False):
        if as_dict:
            return {
                OpenAIFunction.from_function(fn).name: fn for fn in self.function_list
            }
        if as_model:
            return [OpenAIFunction.from_function(fn) for fn in self.function_list]
        return self.function_list

    async def evaluate_function_call(self, Message):
        fn_dict = await self.functions(as_dict=True)
        fn = fn_dict.get(Message.name)
        if fn:
            result = fn(**Message.data.get("result"))
            return result
        return None

    async def start(self, q: str):
        messages = [Message(content=q, role="USER")]
        while not self.stop:
            messages = await self.step(messages)
            if self.stopping_criterion(messages):
                self.stop = True
        return messages

    async def step(self, messages: list[Message]):
        message = await self.engine.run(
            messages=messages, functions=await self.functions(as_model=True)
        )
        if message.role.value == "FUNCTION":
            message = Message(
                role="FUNCTION",
                content=await self.evaluate_function_call(message),
                name=message.name,
            )
        messages.append(message)
        return messages

    def stopping_criterion(self, messages: List[Message]) -> bool:
        last_message = messages[-1] if messages else None
        return bool(last_message and last_message.role.value == "ASSISTANT")
