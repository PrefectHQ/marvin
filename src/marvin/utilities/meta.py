import inspect

from prefect.utilities.asyncutils import sync_compatible

import marvin
from marvin.bots_lab.utilities import mermaid_bot


def enable_mermaid(func):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    @sync_compatible
    async def source_to_mermaid():
        lines, _ = inspect.getsourcelines(func)
        result = ""
        for line in lines:
            stripped_line = line.strip()
            if "@enable_mermaid" not in stripped_line:
                num_spaces = len(line) - len(line.lstrip())
                result += f"{' ' * num_spaces}{stripped_line}\n"
        marvin.get_logger().info((await mermaid_bot.say(result)).content)

    wrapper.to_mermaid = source_to_mermaid
    return wrapper
