from typing import List, Union

from pydantic import PrivateAttr

from marvin.engine.language_models import ChatLLM
from marvin.prompts.base import Prompt, render_prompts
from marvin.utilities.messages import Message
from marvin.utilities.types import LoggerMixin, MarvinBaseModel


class Executor(LoggerMixin, MarvinBaseModel):
    model: ChatLLM
    _should_stop: bool = PrivateAttr(False)

    async def start(
        self,
        prompts: list[Union[Prompt, Message]],
        prompt_render_kwargs: dict = None,
    ) -> list[Message]:
        """
        Start the LLM loop
        """
        # reset stop criteria
        self._should_stop = False

        responses = []
        while not self._should_stop:
            # render the prompts, including any responses from the previous step
            messages = render_prompts(
                prompts + responses,
                render_kwargs=prompt_render_kwargs,
                max_tokens=self.model.context_size,
            )
            response = await self.step(messages)
            responses.append(response)
            if await self.stop_condition(messages, responses):
                self._should_stop = True
        return responses

    async def step(self, messages: list[Message]) -> Message:
        """
        Implements one step of the LLM loop
        """
        messages = await self.process_messages(messages)
        llm_response = await self.run_engine(messages=messages)
        response = await self.process_response(llm_response)
        return response

    async def run_engine(self, messages: list[Message]) -> Message:
        """
        Implements one step of the LLM loop
        """
        llm_response = await self.model.run(messages=messages)
        return llm_response

    async def process_messages(self, messages: list[Message]) -> list[Message]:
        """Called prior to sending messages to the LLM"""
        return messages

    async def stop_condition(
        self, messages: List[Message], responses: List[Message]
    ) -> bool:
        return True

    async def process_response(self, response: Message) -> Message:
        """Called after receiving a response from the LLM"""
        return response
