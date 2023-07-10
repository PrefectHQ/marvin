from typing import Literal

from marvin.engine.language_models import ChatLLM
from marvin.prompts import render_prompts
from marvin.prompts.library import System, User
from marvin.utilities.async_utils import run_sync


class ChoiceSystem(System):
    content = """\
    {{ enum_class_docstring }}
    The user will provide context through text, you will use your expertise 
    to choose the best option below based on it. 
    {% for option in options %}
        {{ loop.index }}. {{ option }}
    {% endfor %}\
    """
    options: list = []
    enum_class_docstring: str = ""


class ChoiceUser(User):
    content = """{{user_input}}"""
    user_input: str


def ai_choice(
    cls=None,
    system=ChoiceSystem,
    user=ChoiceUser,
    method: Literal["logit", "function"] = "logit",
    value_getter=lambda x: x.name,
):
    def decorator(enum_class):
        # Add a new __missing__ method to enum_class
        def _missing_(name):
            model = ChatLLM(max_tokens=1, temperature=0)

            messages = render_prompts(
                [
                    system(
                        enum_class_docstring=enum_class.__doc__,
                        options=[value_getter(option) for option in enum_class],
                    ),
                    user(user_input=name),
                ]
            )

            response = run_sync(
                model.run(
                    messages=messages,
                    logit_bias={
                        next(iter(model.get_tokens(str(i)))): 100
                        for i in range(1, len(enum_class) + 1)
                    },
                )
            )
            return list(enum_class)[int(response.content) - 1]

        enum_class._missing_ = _missing_
        return enum_class

    if cls is None:
        return decorator
    else:
        return decorator(cls)


# from enum import Enum

# @ai_choice
# class CustomerIntent(Enum):
#     '''Classifies the incoming users intent'''
#     SALES = 1
#     TECHNICAL_SUPPORT = 2
#     BILLING_ACCOUNTS = 3
#     PRODUCT_INFORMATION = 4
#     RETURNS_REFUNDS = 5
#     ORDER_STATUS = 6
#     ACCOUNT_CANCELLATION = 7
#     OPERATOR_CUSTOMER_SERVICE = 0


# CustomerIntent("I got double charged, can you help me out?")
