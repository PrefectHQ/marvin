import functools
from typing import Callable, Optional

from prefect import flow as prefect_flow
from pydantic import BaseModel

from marvin.beta.assistants import Thread

from .ai_task import thread_context
from .chat_ui import interactive_chat_server


class AIFlow(BaseModel):
    name: Optional[str] = None
    fn: Callable

    def __call__(self, *args, thread_id: str = None, **kwargs):
        pflow = prefect_flow(name=self.name)(self.fn)

        # Set up the thread context and execute the flow

        # create a new thread for the flow
        thread = Thread(id=thread_id)
        if thread_id is None:
            thread.create()

        # create a holder for the tasks
        tasks = []

        with interactive_chat_server(thread_id=thread.id):
            # enter the thread context
            with thread_context(thread_id=thread.id, tasks=tasks, **kwargs):
                return pflow(*args, **kwargs)


def ai_flow(*args, name=None):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*func_args, **func_kwargs):
            ai_flow_instance = AIFlow(fn=func, name=name or func.__name__)
            return ai_flow_instance(*func_args, **func_kwargs)

        return wrapper

    if args and callable(args[0]):
        return decorator(args[0])

    return decorator
