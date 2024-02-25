import inspect
from contextlib import contextmanager

import marvin
from devtools import debug  # pip install devtools
from marvin.ai.text import ChatRequest, EjectRequest
from marvin.client.openai import AsyncMarvinClient
from marvin.utilities.asyncio import run_sync
from marvin.utilities.context import ctx
from marvin.utilities.strings import count_tokens
from openai.types.chat import ChatCompletion


def process_ejected_request(request: ChatRequest):
    debug(request)
    print(
        f"Message tokens: {count_tokens(''.join(m.content for m in request.messages))}"
    )
    print(f"Called tool: {(t := request.tool_choice.get('function').get('name'))}")
    print("Which looks like:")
    debug(next(iter(tool for tool in request.tools if tool.function.name == t)))


def process_completion(completion: ChatCompletion):
    debug(completion.usage)
    # optionally publish this to a queue


class MyClient(AsyncMarvinClient):
    async def generate_chat(self, **kwargs):
        r = await super().generate_chat(**kwargs)
        maybe_coro = process_completion(r)
        if inspect.iscoroutine(maybe_coro):
            await maybe_coro
        return r


@contextmanager
def inspect_mode(_process_fn=None):
    if _process_fn is None:
        _process_fn = process_ejected_request
    with ctx(eject_request=True):
        try:
            yield
        except EjectRequest as e:
            maybe_coro = _process_fn(e.request)
            if inspect.iscoroutine(maybe_coro):
                run_sync(maybe_coro)


@marvin.fn(client=MyClient())
def list_fruit(n: int = 2) -> list[str]:
    """returns a list of `n` fruit"""


if __name__ == "__main__":
    with inspect_mode():
        list_fruit(n=3)

    print(list_fruit(n=3))
