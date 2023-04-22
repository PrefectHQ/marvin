import asyncio
import inspect
import re
import sys
from functools import partial, wraps
from typing import Any, Callable, TypeVar

from marvin.bot import Bot
from marvin.bot.history import InMemoryHistory
from marvin.utilities.strings import jinja_env

AI_FN_INSTRUCTIONS = jinja_env.from_string(inspect.cleandoc("""
    Your job is to generate outputs for a Python function with the following
    signature and docstring:
    
    {{ function_def }}        
    
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


def ai_fn(
    fn: Callable[[A], T] = None,
    *,
    bot_modifier: Callable = None,
    **bot_kwargs,
) -> Callable[[A], T]:
    """
    @ai_fn
    def rhyme(word: str) -> str:
        "Returns a word that rhymes with the input word."

    rhyme("blue") # "glue"


    Args
        - bot_modifier (Callable):  the `Bot` is passed to this function before
          the function is processed. The function can either modify the bot
          inplace or return a modified bot. Useful for customizing behavior in
          ways that can't easily be passed directly to the bot via kwargs
        - bot_kwargs (dict):  kwargs to pass to the `Bot` constructor

    """
    # this allows the decorator to be used with or without calling it
    if fn is None:
        return partial(ai_fn, bot_modifier=bot_modifier, **bot_kwargs)

    @wraps(fn)
    def ai_fn_wrapper(*args, **kwargs) -> Any:
        wrapper_bot_kwargs = bot_kwargs.copy()

        # Get function signature
        sig = inspect.signature(fn)

        # Bind the provided arguments to the function signature
        bound_args = sig.bind(*args, **kwargs)
        bound_args.apply_defaults()

        # Get the return annotation
        if sig.return_annotation is inspect._empty:
            return_annotation = str
        else:
            return_annotation = sig.return_annotation

        if inspect.isgeneratorfunction(fn):
            gen = fn(*args, **kwargs)
            yield_value = next(gen)
        elif inspect.isasyncgenfunction(fn):
            gen = fn(*args, **kwargs)
            # 3.10 introduces "anext", otherwise use __anext__
            if sys.version_info >= (3, 10):
                yield_value = asyncio.run(anext(gen))
            else:
                yield_value = asyncio.run(gen.__anext__())
        else:
            yield_value = None

        # get the function source code - it will include the @ai_fn decorator,
        # which can confuse the AI, so we use regex to only get the function
        # that is being decorated
        function_def = inspect.cleandoc(inspect.getsource(fn))
        function_def = re.search(
            re.compile(r"(\bdef\b.*)", re.DOTALL), function_def
        ).group(0)

        # Build the instructions
        instructions = AI_FN_INSTRUCTIONS.render(
            function_def=function_def,
            function_name=fn.__name__,
        )

        # ai_fns have no plugins by default
        if "plugins" not in wrapper_bot_kwargs:
            wrapper_bot_kwargs["plugins"] = []

        # ai functions do not persist by default
        if "history" not in wrapper_bot_kwargs:
            wrapper_bot_kwargs["history"] = InMemoryHistory()

        # create the bot
        bot = Bot(
            instructions=instructions,
            personality=AI_FN_PERSONALITY,
            response_format=return_annotation,
            **wrapper_bot_kwargs,
        )

        if bot_modifier is not None:
            modified_bot = bot_modifier(bot)
            # bot might not be modified inplace
            if modified_bot is not None:
                bot = modified_bot

        # build the message
        message = AI_FN_MESSAGE.render(
            input_binds=bound_args.arguments,
            yield_value=yield_value,
        )

        async def run_ai_function():
            response = await bot.say(message)
            return response.parsed_content

        if inspect.iscoroutinefunction(fn):
            return run_ai_function()
        else:
            return asyncio.run(run_ai_function())

    ai_fn_wrapper.fn = fn

    return ai_fn_wrapper
