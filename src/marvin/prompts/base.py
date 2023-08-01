import abc
import inspect
from typing import Union

from pydantic import BaseModel, Field

import marvin
from marvin.utilities.messages import Message, Role
from marvin.utilities.strings import count_tokens, jinja_env


class PromptList(list[Union["Prompt", Message]]):
    def __init__(self, prompts: list[Union["Prompt", Message]]):
        super().__init__(prompts)

    def render(self, **kwargs):
        return render_prompts(self, render_kwargs=kwargs)

    def dict(self, **kwargs):
        return [message.dict() for message in self.render(**kwargs)]

    def __call__(self, **kwargs):
        return self.render(**kwargs)


class Prompt(BaseModel, abc.ABC):
    """
    Base class for prompt templates.
    """

    position: int = Field(
        None,
        repr=False,
        description=(
            "Position indicates the desired index for this prompt's messages. 0"
            " indicates they should be first; 1 indicates they should be second; -1"
            " indicates they should be last; None indicates they should be between any"
            " prompts that do request a position."
        ),
    )
    priority: float = Field(
        10,
        repr=False,
        description=(
            "Priority indicates the weight given when trimming messages to satisfy"
            " context limitations. Lower numbers indicate higher priority e.g. the"
            " highest priority is 0. The default is 10. Ties will be broken by message"
            " timestamp and role."
        ),
    )

    @abc.abstractmethod
    def generate(self, **kwargs) -> list["Message"]:
        """
        Abstract method that generates a list of messages from the prompt template
        """
        pass

    def render(self, content, render_kwargs: dict = None):
        """
        Helper function for rendering any jinja2 template with runtime render kwargs
        """
        return jinja_env.from_string(inspect.cleandoc(content)).render(
            **(render_kwargs or {})
        )

    def __or__(self, other):
        """
        Supports pipe syntax:
        prompt = (
            Prompt()
            | Prompt()
            | Prompt()
        )
        """
        # when the right operand is a Prompt object
        if isinstance(other, Prompt):
            return PromptList([self, other])
        # when the right operand is a list
        elif isinstance(other, list):
            return PromptList([self] + other)
        else:
            raise TypeError(
                f"unsupported operand type(s) for |: '{type(self).__name__}' and"
                f" '{type(other).__name__}'"
            )

    def __ror__(self, other):
        """
        Supports pipe syntax:
        prompt = (
            Prompt()
            | Prompt()
            | Prompt()
        )
        """
        # when the left operand is a Prompt object
        if isinstance(other, Prompt):
            return PromptList([other, self])
        # when the left operand is a list
        elif isinstance(other, list):
            return PromptList(other + [self])
        else:
            raise TypeError(
                f"unsupported operand type(s) for |: '{type(other).__name__}' and"
                f" '{type(self).__name__}'"
            )


class MessageWrapper(Prompt):
    """
    A Prompt class that stores and returns a specific Message
    """

    message: Message

    def generate(self, **kwargs) -> list[Message]:
        return [self.message]


def render_prompts(
    prompts: list[Union[Prompt, Message]], render_kwargs: dict = None, max_tokens=None
) -> list[Message]:
    max_tokens = max_tokens or marvin.settings.llm_max_context_tokens

    all_messages = []

    # if the user supplied any messages, wrap them in a MessageWrapper so we can
    # treat them as prompts for sorting and filtering
    prompts = [
        MessageWrapper(message=p) if isinstance(p, Message) else p for p in prompts
    ]

    # Separate prompts by positive, none and negative position
    pos_prompts = [p for p in prompts if p.position is not None and p.position >= 0]
    none_prompts = [p for p in prompts if p.position is None]
    neg_prompts = [p for p in prompts if p.position is not None and p.position < 0]

    # Sort the positive prompts in ascending order and negative prompts in
    # descending order, but both with timestamp ascending
    pos_prompts = sorted(pos_prompts, key=lambda c: c.position)
    neg_prompts = sorted(neg_prompts, key=lambda c: c.position, reverse=True)

    # generate messages from all prompts
    for i, prompt in enumerate(pos_prompts + none_prompts + neg_prompts):
        prompt_messages = prompt.generate(**(render_kwargs or {})) or []
        all_messages.extend((prompt.priority, i, m) for m in prompt_messages)

    # sort all messages by (priority asc, position desc)  and stop when the
    # token limit is reached. This will prefer high-priority messages that are
    # later in the message chain.
    current_tokens = 0
    allowed_messages = []
    for _, position, msg in sorted(all_messages, key=lambda m: (m[0], -1 * m[1])):
        if current_tokens >= max_tokens:
            break
        allowed_messages.append((position, msg))
        current_tokens += count_tokens(msg.content)

    # sort allowed messages by position to restore original order
    messages = [msg for _, msg in sorted(allowed_messages, key=lambda m: m[0])]

    # Combine all system messages into one and insert at the index of the first
    # system message
    system_messages = [m for m in messages if m.role == Role.SYSTEM]
    if len(system_messages) > 1:
        system_message = Message(
            role=Role.SYSTEM,
            content="\n\n".join([m.content for m in system_messages]),
        )
        system_message_index = messages.index(system_messages[0])
        messages = [m for m in messages if m.role != Role.SYSTEM]
        messages.insert(system_message_index, system_message)

    # return all messages
    return messages
