import asyncio
import inspect
import re
from functools import partial, wraps
from typing import Any, Callable

from marvin.bot import Bot
from marvin.utilities.strings import jinja_env

AI_FN_INSTRUCTIONS = jinja_env.from_string(
    inspect.cleandoc(
        """
        Your job is to generate outputs for a Python function with the following
        signature:
        
        {{ function_def }}
        
        
        You can not see all of the function's source code, just its signature
        and docstring. However, to assist you, the user may have modified the
        function to return values that will help when generating outputs. You
        will be provided any values returned from the function but you should
        NOT assume they are actual outputs of the full function. Treat any
        source code (and returned values) as preproccesing.        
        
        The user will give you inputs to this function and you must respond with
        its result, in the appropriate form. Do not describe your process or
        explain your answer, and do not give the user any additional
        instruction. Respond ONLY with the return value of the function.
        
        Note: you can NOT run this function ({{ function_name }}) as a plugin.
        """
    )
)

AI_FN_PERSONALITY = inspect.cleandoc(
    """
    You love to generate the correct answer, but you do not want to engage the
    user in any way, including explaining your work, giving further
    instructions, or asking for clarification.
    """
)

AI_FN_MESSAGE = jinja_env.from_string(
    inspect.cleandoc(
        """
        {% if input_binds %} 
        The user supplied the following inputs:
        
        {%for desc in input_binds%}
        {{ desc }}
        
        {% endfor %}
        {% endif -%}
        
        {% if return_value %} 
        In addition, the user called the function as-is and got the following
        return value: 
        
        {{ return_value }} 
        {% endif %}
        
        
        Respond with a result of the function call. Do not give any additional
        detail, instructions, or even punctuation; respond ONLY with the output.
        Do not explain the type signature or give guidance on parsing.
        """
    )
)


def ai_fn(
    fn: Callable = None,
    *,
    bot_modifier: Callable = None,
    call_function: bool = True,
    **bot_kwargs,
) -> Callable:
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
        - call_function (bool):  if True, the function will be called and the
          return value will be included in the message
        - bot_kwargs (dict):  kwargs to pass to the `Bot` constructor

    """
    # this allows the decorator to be used with or without calling it
    if fn is None:
        return partial(
            ai_fn,
            bot_modifier=bot_modifier,
            call_function=call_function,
            **bot_kwargs,
        )

    @wraps(fn)
    def ai_fn_wrapper(*args, **kwargs) -> Any:
        bot_kwargs = {}

        # Get function signature
        sig = inspect.signature(fn)

        # Bind the provided arguments to the function signature
        bound_args = sig.bind(*args, **kwargs)
        bound_args.apply_defaults()

        # Build input binds
        input_binds = []
        for k, v in bound_args.arguments.items():
            input_binds.append(f"{k} = {v}")

        # see if the function preprocesses the inputs
        if call_function:
            if inspect.iscoroutinefunction(fn):
                return_value = asyncio.run(fn(*args, **kwargs))
            else:
                return_value = fn(*args, **kwargs)
        else:
            return_value = None

        # Get the return annotation
        if sig.return_annotation is inspect._empty:
            return_annotation = str
        else:
            return_annotation = sig.return_annotation

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
        if "plugins" not in bot_kwargs:
            bot_kwargs["plugins"] = []

        # create the bot
        bot = Bot(
            instructions=instructions,
            personality=AI_FN_PERSONALITY,
            response_format=return_annotation,
            **bot_kwargs,
        )

        if bot_modifier is not None:
            modified_bot = bot_modifier(bot)
            # bot might not be modified inplace
            if modified_bot is not None:
                bot = modified_bot

        # build the message
        message = AI_FN_MESSAGE.render(
            input_binds=input_binds, return_value=return_value
        )

        async def get_response():
            response = await bot.say(message)
            return response.parsed_content

        if inspect.iscoroutinefunction(fn):
            return get_response()
        else:
            return asyncio.run(get_response())

    ai_fn_wrapper.fn = fn

    return ai_fn_wrapper
