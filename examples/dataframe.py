# /// script
# dependencies = ["pandas", "marvin@git+https://github.com/prefecthq/marvin.git"]
# ///

"""
fills out a new column in a dataframe
"""

from typing import Annotated

import pandas as pd
from pydantic import Field

import marvin

ColumnValue = Annotated[
    str, Field(description="word for sum of the two numbers in the row")
]

if __name__ == "__main__":
    df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})

    new_column_values = marvin.run(
        result_type=list[ColumnValue],
        context={"a": df["a"], "b": df["b"]},
        instructions="fill out a new column in the dataframe",
    )
    new_column = pd.Series(new_column_values, dtype=str)
    df["c"] = new_column

    print(df)
