import pytest

from marvin.prompts import Prompt


def greet_name(name: str):
    """USER: Hello {{ name }}"""


def greet_param(param: str):
    """USER: Hello {{ param }}"""


def greet_untyped(city):
    """USER: Hello {{ city }}"""


def greet_default(city: str, salutation="Hello"):
    """USER: {{ salutation }} {{ city }}"""


def greet_typed(city: str):
    """USER: Hello {{ city }}"""


@pytest.mark.parametrize(
    "fn, kwargs",
    [
        (greet_name, {"name": "Ada"}),
        (greet_param, {"param": "Ada"}),
        (greet_untyped, {"city": "Ada"}),
        (greet_default, {"city": "Ada"}),
        (greet_typed, {"city": "Ada"}),
    ],
)
def test_from_fn_renders_function_parameters(fn, kwargs):
    prompt_type = Prompt.from_fn(fn)
    prompt = prompt_type(**kwargs)
    messages = prompt.to_messages()

    assert len(messages) == 1
    assert messages[0].parts[0].content == "Hello Ada"


def test_from_fn_allows_overriding_unannotated_default():
    prompt_type = Prompt.from_fn(greet_default)
    prompt = prompt_type(city="Ada", salutation="Welcome")
    assert prompt.to_messages()[0].parts[0].content == "Welcome Ada"
