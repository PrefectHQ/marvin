import abc

from pydantic import BaseModel, Field, validator

import marvin
from marvin.models.messages import Message, Role


class History(BaseModel):
    messages: list[Message] = Field(default_factory=list)

    def add_message(self, message: Message):
        self.messages.append(message)

    def get_messages(self, n: int = None) -> list[Message]:
        if n is None:
            return self.messages.copy()
        return self.messages[-n:]

    def clear(self):
        self.messages.clear()


class Prompt(BaseModel, abc.ABC):
    position: int = None

    @abc.abstractmethod
    def generate(self) -> list["Message"]:
        pass


class MessageHistory(Prompt):
    history: History
    max_messages: int = 100

    def generate(self) -> list[Message]:
        return self.history.get_messages(n=self.max_messages)


class System(Prompt):
    position: int = 0
    template: str

    def generate(self) -> list[Message]:
        return [Message(role=Role.SYSTEM, content=self.template)]


class ChainOfThought(Prompt):
    position: int = -1

    def generate(self) -> list[Message]:
        return [Message(role=Role.ASSISTANT, content="Let's think step by step")]


class Model(BaseModel):
    name: str = None
    model: str = Field(default="gpt-3.5-turbo-0613")
    max_tokens: int = Field(default=4000)
    temperature: float = Field(default=0.1)
    stream: bool = Field(default=False)

    prompts: list[Prompt] = Field(default_factory=list)

    @validator("name", always=True)
    def default_name(cls, v):
        if v is None:
            v = cls.__name__
        return v

    def __or__(self, prompt: Prompt):
        if not isinstance(prompt, Prompt):
            raise TypeError(f"Expected Prompt, got {type(prompt)}")
        new_model = self.copy()
        new_model.prompts = self.prompts + [prompt]
        return new_model

    def render_prompts(self) -> list[Message]:
        messages = []

        # Separate prompts by positive, none and negative position
        pos_prompts = [
            p for p in self.prompts if p.position is not None and p.position >= 0
        ]
        none_prompts = [p for p in self.prompts if p.position is None]
        neg_prompts = [
            p for p in self.prompts if p.position is not None and p.position < 0
        ]

        # Sort the positive prompts in ascending order and negative prompts in
        # descending order, but both with timestamp ascending
        pos_prompts = sorted(pos_prompts, key=lambda c: c.position)
        neg_prompts = sorted(neg_prompts, key=lambda c: c.position, reverse=True)

        for prompt in pos_prompts + none_prompts + neg_prompts:
            messages.extend(prompt.generate())

        # Combine all system messages into one and insert at the index of
        # the first system message
        system_messages = [m for m in messages if m.role == Role.SYSTEM]
        if len(system_messages) > 1:
            system_message = Message(
                role=Role.SYSTEM,
                content="\n\n".join([m.content for m in system_messages]),
            )
            system_message_index = messages.index(system_messages[0])
            messages = [m for m in messages if m.role != Role.SYSTEM]
            messages.insert(system_message_index, system_message)

        return messages

    def generate(self) -> list[Message]:
        return self.render_prompts()


class AIApplication(BaseModel):
    model: Model = Field(default_factory=lambda: Model(model="gpt-3.5-turbo-0613"))
    prompts: list[Prompt] = Field(default_factory=list)
    history: History = Field(default_factory=History)

    def trim_messages(
        self,
        messages: list[Message],
        max_tokens: int = marvin.settings.llm_max_tokens,
    ) -> list[Message]:
        # Implement the trimming logic here
        return messages

    async def run(self, user_input: str):
        self.history.add_message(user_input)
        function_history = History()

        self.model.prompts = self.prompts + [
            MessageHistory(history=self.history),
            MessageHistory(history=function_history, position=-1),
        ]

        while True:
            # Render all prompts
            messages = self.model.render_prompts()
            trimmed_messages = self.trim_messages(messages)

            # Call LLM
            llm_output = await marvin.utilities.llms.call_llm_messages(
                llm=self.model,
                messages=trimmed_messages,
            )

            if llm_output.role == "FUNCTION":
                function_history.add_message(llm_output)
            else:
                self.user_history.add_message(llm_output)
                return llm_output
