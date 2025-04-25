"""
This DX is supported but not encouraged for those who want type safety. See `cast` or `extract` for more.
"""

from datetime import date
from typing import TypedDict

from marvin import fn


class CulturalReference(TypedDict):
    short_description: str
    circa: date


@fn(prompt="provide likely outputs for this function, and use ALL CAPS!")
def pop_culture_related_to_sum(x: int, y: int) -> CulturalReference:
    """Given two numbers, return a cultural reference related to the sum of the two numbers."""
    return f"the sum of {x} and {y} is {x + y}"  # type: ignore[reportReturnType]


if __name__ == "__main__":
    print(pop_culture_related_to_sum(40, 2))
"""
» uv run examples/hello_fn.py
╭─ Agent "Marvin" (0e8e4dc7) ──────────────────────────────────────────────────────────────────────╮
│                                                                                                  │
│  Tool:    Mark Task 910991c9 ("Predict output of pop_culture_related_to_sum") successful         │
│  Status:  ✅                                                                                     │
│  Result   {                                                                                      │
│               'short_description': 'THE ANSWER TO THE ULTIMATE QUESTION OF LIFE, THE UNIVERSE,   │
│           AND EVERYTHING',                                                                       │
│               'circa': '1979-10-12'                                                              │
│           }                                                                                      │
│                                                                                                  │
╰────────────────────────────────────────────────────────────────────────────────────  1:50:52 AM ─╯
{'short_description': 'THE ANSWER TO THE ULTIMATE QUESTION OF LIFE, THE UNIVERSE, AND EVERYTHING', 'circa': datetime.date(1979, 10, 12)}
"""
