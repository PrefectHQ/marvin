from marvin.models.messages import Message, Role
from marvin.prompts import Prompt


def render_prompts(prompts: list[Prompt], render_kwargs: dict = None) -> list[Message]:
    messages = []

    # Separate prompts by positive, none and negative position
    pos_prompts = [p for p in prompts if p.position is not None and p.position >= 0]
    none_prompts = [p for p in prompts if p.position is None]
    neg_prompts = [p for p in prompts if p.position is not None and p.position < 0]

    # Sort the positive prompts in ascending order and negative prompts in
    # descending order, but both with timestamp ascending
    pos_prompts = sorted(pos_prompts, key=lambda c: c.position)
    neg_prompts = sorted(neg_prompts, key=lambda c: c.position, reverse=True)

    # generate messages from all prompts
    for prompt in pos_prompts + none_prompts + neg_prompts:
        messages.extend(prompt.generate())

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

    # render all messages
    messages = [m.render(**render_kwargs) for m in messages]

    # return all messages
    return messages
