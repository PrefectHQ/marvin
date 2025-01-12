from typing import Annotated

from pydantic import Field, TypeAdapter

import marvin

# you can use Annotated to add extra detail to your types
Fruit = Annotated[str, Field(description="A fruit")]


if __name__ == "__main__":
    fruits = marvin.generate(target=Fruit, n=3, instructions="high vitamin C content")
    assert len(fruits) == 3
    print("results are a valid list of Fruit:")
    print(f"{TypeAdapter(list[Fruit]).validate_python(fruits)}")

    print(
        marvin.generate(
            target=str,
            n=len(fruits),
            instructions=f"bizarro sitcom character names based on these fruit: {fruits}",
        ),
    )
"""
» python examples/hello.py
╭─ Marvin ─────────────────────────────────────────────────────────────────────────────────────────╮
│ ⠋   Final Result                                                                                 │
│     Input:   {                                                                                   │
│                'response': {                                                                     │
│                  'task_id': '5dbe8a4e-31c4-44f6-84ae-3642d126485a',                              │
│                  'result': [                                                                     │
│                    'Orange',                                                                     │
│                    'Kiwi',                                                                       │
│                    'Strawberry'                                                                  │
│                  ]                                                                               │
│                }                                                                                 │
│              }                                                                                   │
╰──────────────────────────────────────────────────────────────────────────────────── 11:14:12 PM ─╯
results are a valid list of Fruit:
['Orange', 'Kiwi', 'Strawberry']
╭─ Marvin ─────────────────────────────────────────────────────────────────────────────────────────╮
│ ⠹   Final Result                                                                                 │
│     Input:   {                                                                                   │
│                'response': {                                                                     │
│                  'task_id': 'd0ca22f0-d636-48f1-b522-6e613e146953',                              │
│                  'result': [                                                                     │
│                    'Orangey McPeelson',                                                          │
│                    'Kiwi Kookaburra',                                                            │
│                    'Strawberry Sassafras'                                                        │
│                  ]                                                                               │
│                }                                                                                 │
│              }                                                                                   │
╰──────────────────────────────────────────────────────────────────────────────────── 11:14:13 PM ─╯
['Orangey McPeelson', 'Kiwi Kookaburra', 'Strawberry Sassafras']
"""
