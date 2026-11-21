import pytest
from pydantic_ai import ImageUrl

from marvin import Task


@pytest.mark.parametrize("sequence_type", [list, tuple])
def test_mixed_instructions_preserve_supplied_attachments(sequence_type):
    supplied = sequence_type([ImageUrl("https://example.com/reference.png")])
    inline = ImageUrl("https://example.com/question.png")

    task = Task(instructions=["Compare these images", inline], attachments=supplied)

    assert list(supplied) == [ImageUrl("https://example.com/reference.png")]
    assert task.get_prompt()[1:] == [
        ImageUrl("https://example.com/reference.png"),
        inline,
    ]


def test_reusing_attachments_does_not_change_earlier_task():
    supplied = [ImageUrl("https://example.com/reference.png")]
    first = Task(instructions="Describe the reference", attachments=supplied)
    second = Task(
        instructions=["Compare", ImageUrl("https://example.com/other.png")],
        attachments=supplied,
    )

    assert first.get_prompt()[1:] == [ImageUrl("https://example.com/reference.png")]
    assert len(second.get_prompt()[1:]) == 2


def test_mixed_instructions_without_separate_attachments():
    inline = ImageUrl("https://example.com/question.png")
    task = Task(instructions=["Describe", inline])
    assert task.get_prompt()[1:] == [inline]
