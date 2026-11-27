import pytest

from marvin.prompts import Prompt


@pytest.mark.parametrize("prefix", ["\n", " \n\n", ""])
def test_whitespace_before_first_role(prefix):
    prompt = Prompt(source=prefix + "SYSTEM: Be brief.\nUSER: Hello")
    assert [
        (m.parts[0].part_kind, m.parts[0].content) for m in prompt.to_messages()
    ] == [
        ("system-prompt", "Be brief."),
        ("user-prompt", "Hello"),
    ]


def test_text_before_first_role():
    prompt = Prompt(source="A note\nSYSTEM: Be brief.")
    assert [
        (m.parts[0].part_kind, m.parts[0].content) for m in prompt.to_messages()
    ] == [
        ("user-prompt", "A note"),
        ("system-prompt", "Be brief."),
    ]
