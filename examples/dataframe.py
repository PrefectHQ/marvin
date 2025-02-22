# /// script
# dependencies = ["pandas", "marvin@git+https://github.com/prefecthq/marvin.git"]
# ///

"""
fills out a new column in a dataframe, adding values to many columns concurrently
"""

import asyncio
import sys
from typing import Annotated

import numpy
import pandas as pd
from pydantic import Field

import marvin


async def add_columns(df: pd.DataFrame, new_column_names: list[str]) -> pd.DataFrame:
    new_column_values = await asyncio.gather(
        *[
            marvin.run_async(
                result_type=Annotated[
                    str, Field(description="UPPERCASE", max_length=15)
                ],
                instructions="select the most plausibly correct value for the new column",
                context={
                    "column name": column_name,
                    "existing row": row[1].to_dict(),  # type: ignore
                },
            )
            for column_name in new_column_names
            for row in df.iterrows()
        ]
    )

    print(f"\nAdded {new_column_names=} to dataframe\n")
    df[new_column_names] = numpy.array(new_column_values).reshape(-1, len(df)).T
    return df


if __name__ == "__main__":
    """
    uv run examples/dataframe.py <new_column_names> <df_csv_path>

    example:
        >> uv run examples/dataframe.py hometown,age,gender path/to/dataframe.csv
    """

    DEFAULT_DF = pd.DataFrame(
        {
            "Name": [
                "Stevie Ray Vaughan",
                "Doechii",
                "Bill Evans",
                "Nardwuar",
                "Marie Curie",
            ],
        }
    )
    new_column_names = (
        sys.argv[1] if len(sys.argv) > 1 else "known for,birth year"
    ).split(",")

    df_path = sys.argv[2] if len(sys.argv) > 2 else None
    df = pd.read_csv(df_path) if df_path else DEFAULT_DF  # type: ignore
    print(asyncio.run(add_columns(df, new_column_names)))
