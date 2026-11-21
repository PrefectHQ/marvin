from dataclasses import asdict, dataclass

from marvin.prompts import Prompt


@dataclass
class Greeting(Prompt):
    name: str = "world"


def test_prompt_field_matches_rendered_value():
    prompt = Greeting(source="USER: Hello {{ name }}", name="Ada")
    assert prompt.name == "Ada"
    assert prompt.to_messages()[0].parts[0].content == "Hello Ada"


def test_prompt_field_assignment_updates_the_attribute_and_template():
    prompt = Greeting(source="USER: Hello {{ name }}")
    prompt.name = "Grace"
    assert prompt.name == "Grace"
    assert prompt.to_messages()[0].parts[0].content == "Hello Grace"


def test_prompt_dataclass_serialization_uses_current_field_value():
    prompt = Greeting(source="USER: Hello {{ name }}", name="Ada")
    assert asdict(prompt)["name"] == "Ada"


def test_prompt_still_renders_dynamic_attributes():
    prompt = Prompt(source="USER: Hello {{ name }}")
    prompt.name = "Ada"
    assert prompt.name == "Ada"
    assert prompt.to_messages()[0].parts[0].content == "Hello Ada"
