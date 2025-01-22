"""
This DX is supported but not encouraged for those who want type safety. See `cast` or `extract` for more.
"""

from datetime import date
from typing import TypedDict

from marvin import fn


class CulturalReference(TypedDict):
    short_description: str
    circa: date


@fn
def pop_culture_related_to_sum(x: int, y: int) -> CulturalReference:
    """Given two numbers, return a cultural reference related to the sum of the two numbers."""
    return f"the sum of {x} and {y} is {x + y}"  # type: ignore[reportReturnType]


if __name__ == "__main__":
    print(pop_culture_related_to_sum(40, 2))
"""
» python examples/hello_fn.py
╭─ Marvin ─────────────────────────────────────────────────────────────────────────────────────────╮
│ ⠋   Final Result                                                                                 │
│     Input:   {                                                                                   │
│                'response': {                                                                     │
│                  'task_id': 'a9afe620-be14-4511-a2ab-37e026eedcc3',                              │
│                  'result': {                                                                     │
│                    'short_description': "The number 42 is widely recognized as 'The Answer to    │
│              the Ultimate Question of Life, the Universe, and Everything' from Douglas Adams'    │
│              science fiction series 'The Hitchhiker's Guide to the Galaxy'.",                    │
│                    'circa': '1979-01-01'                                                         │
│                  }                                                                               │
│                }                                                                                 │
│              }                                                                                   │
╰──────────────────────────────────────────────────────────────────────────────────── 11:23:05 PM ─╯
{
    'short_description': "The number 42 is widely recognized as 'The Answer to the Ultimate Question of Life, the Universe, and Everything' from Douglas Adams' science fiction series 'The Hitchhiker's Guide to the Galaxy'.",
    'circa': datetime.date(1979, 1, 1)
}
"""
