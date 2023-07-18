from marvin.engine.language_models import ChatLLM, chat_llm
from marvin.prompts import render_prompts
from marvin.prompts.library import System, User
from marvin.utilities.async_utils import run_sync


class ClassifierSystem(System):
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


class ClassifierUser(User):
    content = """{{user_input}}"""
    user_input: str


def ai_classifier(
    cls=None,
    model: ChatLLM = None,
    # system_prompt:Prompt=None,
    # user_prompt:Prompt=None,
    # method: Literal["logit", "function"] = "logit",
    # value_getter:Callable=None,
):
    # placeholder until kwargs are exposed
    system_prompt, user_prompt, value_getter = None, None, None

    if model is None:
        model = chat_llm(max_tokens=1, temperature=0)
    elif model.max_tokens != 1:
        raise ValueError(
            "The model must be configured with max_tokens=1 to use ai_classifier"
        )
    if system_prompt is None:
        system_prompt = ClassifierSystem
    if user_prompt is None:
        user_prompt = ClassifierUser
    if value_getter is None:

        def value_getter(x):
            return x.name

    def decorator(enum_class):
        # Add a new __missing__ method to enum_class to intercept NLP prompts
        def _missing_(name):
            messages = render_prompts(
                [
                    system_prompt(
                        enum_class_docstring=enum_class.__doc__ or "",
                        options=[value_getter(option) for option in enum_class],
                    ),
                    user_prompt(user_input=name),
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
