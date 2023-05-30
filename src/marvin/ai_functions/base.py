import asyncio
import inspect
import re
import sys
from functools import partial
from typing import Any, Callable, Dict, List, TypeVar

from prefect import flow, task
from prefect.utilities.asyncutils import sync_compatible

from marvin.bot import Bot
from marvin.bot.history import InMemoryHistory
from marvin.utilities.strings import jinja_env

AI_FN_INSTRUCTIONS = jinja_env.from_string(inspect.cleandoc("""
    ## Objective
    
    Your job is to generate outputs for a Python function with the following
    signature and docstring:
    
    {{ function_def }}        
    
    {% if function_description %}
    The following description was also provided:
    
    {{ function_description }}
    {% endif %}
    
    ## Instructions
    
    When the function is called, you will be provided with its inputs (if any)
    and must respond with the most likely result. If it `yields`, you will also
    be provided with any yielded values. Any source code you see is only for
    generating yielded values at runtime, it is not the actual source code of
    the function. Do not give any additional detail, instructions, or even
    punctuation; respond ONLY with a return value that can be parsed into the
    expected form.
    """))

AI_FN_PERSONALITY = inspect.cleandoc("""
    You generate answers, but do not want to engage the user in any way,
    including explaining your work, giving further instructions, or asking for
    clarification.
    """)

AI_FN_MESSAGE = jinja_env.from_string(inspect.cleandoc("""
    # Inputs
    
    {% if input_binds %} 
    The function was called with these inputs:
    
    {%for (arg, value) in input_binds.items()%}
    - {{ arg }}: {{ value }}
    
    {% endfor %}
    {% else %}
    The function was called without inputs.
    {% endif -%}
    
    {% if yield_value %}
    # Yield value
    
    {{ yield_value }}
    {% endif %}
    
    # Instructions 
    Generate the function's output. Do not explain the type signature or give
    guidance on parsing.
    """))

T = TypeVar("T")
A = TypeVar("A")


class AIFunction:
    def __init__(
        self,
        *,
        fn: Callable = None,
        name: str = None,
        description: str = None,
        bot: Bot = None,
        bot_kwargs: dict = None,
    ):
        if fn is None:
            fn = self.run
        self.fn = fn
        self.name = name or fn.__name__
        self.description = description or fn.__doc__

        if bot_kwargs is not None and bot is not None:
            raise ValueError(
                "bot and bot_kwargs cannot both be provided. "
                "bot_kwargs will be passed to the Bot constructor, "
                "and bot will be used as the bot instance."
            )
        self._bot = bot
        self._bot_kwargs = bot_kwargs or {}
        super().__init__()

    def __repr__(self):
        return f"<AIFunction {self.name}>"

    def get_bot(self):
        if self._bot is not None:
            return self._bot

        bot_kwargs = self._bot_kwargs.copy()

        # Get the return annotation
        sig = inspect.signature(self.fn)

        if sig.return_annotation is inspect._empty:
            return_annotation = str
        else:
            return_annotation = sig.return_annotation

        # get the function source code - it might include the @ai_fn decorator,
        # which can confuse the AI, so we use regex to only get the function
        # that is being decorated
        function_def = inspect.cleandoc(inspect.getsource(self.fn))
        if match := re.search(re.compile(r"(\bdef\b.*)", re.DOTALL), function_def):
            function_def = match.group(0)

        # ai_fns have no plugins by default
        if "plugins" not in bot_kwargs:
            bot_kwargs["plugins"] = []
        # ai functions do not persist by default
        if "history" not in bot_kwargs:
            bot_kwargs["history"] = InMemoryHistory()
        if "response_format" not in bot_kwargs:
            bot_kwargs["response_format"] = return_annotation
        if "personality" not in bot_kwargs:
            bot_kwargs["personality"] = AI_FN_PERSONALITY
        if "instructions" not in bot_kwargs:
            bot_kwargs["instructions"] = AI_FN_INSTRUCTIONS.render(
                function_def=function_def,
                function_name=self.fn.__name__,
                function_description=(
                    self.description if self.description != self.fn.__doc__ else None
                ),
            )
        if "instructions" not in bot_kwargs:
            bot_kwargs["instructions"] = AI_FN_PERSONALITY

        bot = Bot(**bot_kwargs)
        return bot

    def __call__(self, *args, **kwargs):
        output = self._run(*args, **kwargs)

        # if the provided fn is not async, run it immediately
        if not inspect.iscoroutinefunction(self.fn):
            output = asyncio.run(output)

        return output

    async def __prompt__(self, *args, **kwargs):
        # Get function signature
        sig = inspect.signature(self.fn)

        # Bind the provided arguments to the function signature
        bound_args = sig.bind(*args, **kwargs)
        bound_args.apply_defaults()

        if inspect.isgeneratorfunction(self.fn):
            gen = self.fn(*args, **kwargs)
            yield_value = next(gen)
        elif inspect.isasyncgenfunction(self.fn):
            gen = self.fn(*args, **kwargs)
            # 3.10 introduces "anext", otherwise use __anext__
            if sys.version_info >= (3, 10):
                yield_value = await anext(gen)
            else:
                yield_value = await gen.__anext__()
        else:
            yield_value = None

        # build the message
        message = AI_FN_MESSAGE.render(
            input_binds=bound_args.arguments,
            yield_value=yield_value,
        )
        return message

    async def _run(self, *args, **kwargs):
        message = await self.__prompt__(*args, **kwargs)
        bot = self.get_bot()
        response = await bot.say(message)
        return response.parsed_content

    def run(self, *args, **kwargs):
        """
        Override this to create the AI function as an instance method instead of
        a passed function
        """
        raise NotImplementedError()

    @sync_compatible
    async def map(
        self,
        *args,
        task_kwargs: Dict[str, Any] = None,
        flow_kwargs: Dict[str, Any] = None,
        **kwargs,
    ) -> List[T]:
        @task(**{"name": self.fn.__name__, **(task_kwargs or {})})
        async def process_item(item: Any):
            return await self._run(item, **kwargs)

        @flow(**{"name": self.fn.__name__, **(flow_kwargs or {})})
        async def mapped_ai_fn(*args, **kwargs):
            return await process_item.map(*args, **kwargs)

        return [
            await state.result().get() for state in await mapped_ai_fn(*args, **kwargs)
        ]


def ai_fn(
    fn: Callable[[A], T] = None,
    *,
    bot: Bot = None,
    **bot_kwargs,
) -> Callable[[A], T]:
    """
    @ai_fn
    def rhyme(word: str) -> str:
        "Returns a word that rhymes with the input word."

    rhyme("blue") # "glue"


    Args
        - bot (Bot): a bot instance to use for the AI function
        - bot_kwargs (dict):  kwargs to pass to the `Bot` constructor

    """
    # this allows the decorator to be used with or without calling it
    if fn is None:
        return partial(ai_fn, bot=bot, **bot_kwargs)
    return AIFunction(fn=fn, bot=bot, bot_kwargs=bot_kwargs)
