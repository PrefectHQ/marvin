# /// script
# dependencies = ["pandas", "marvin@git+https://github.com/prefecthq/marvin.git"]
# ///

"""
fills out a new column in a dataframe
"""

import sys
from dataclasses import dataclass
from typing import Any

import pandas as pd

import marvin


@dataclass
class NewColumn:
    name: str
    row_values: list[Any]


if __name__ == "__main__":
    """
    uv run examples/dataframe.py <new_column_name> <df_path>
    """
    new_column_name = sys.argv[1] if len(sys.argv) > 1 else "home city"
    df_path = sys.argv[2] if len(sys.argv) > 2 else None

    df = (
        pd.read_csv(df_path)  # type: ignore
        if df_path
        else pd.DataFrame(
            {
                "Name": ["SRV", "Doechii", "Gandhi"],
                "Known For": [
                    "Prolific blues guitarist",
                    "Newly arrived rap queen",
                    "Indian Independence Movement",
                ],
            }
        )
    )

    new_column = marvin.run(
        result_type=NewColumn,
        instructions="fill out a new column in the dataframe",
        context={
            "Desired Column Name": new_column_name,
            "Name": df["Name"],
            "Known For": df["Known For"],
        },
    )

    df[new_column.name] = pd.Series(
        new_column.row_values,
        dtype=str,
        name=new_column.name,
    )

    print(df)
