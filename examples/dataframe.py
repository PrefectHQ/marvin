# /// script
# dependencies = ["pandas"]
# ///

"""
fills out a new column in a dataframe
"""

import marvin
import pandas as pd


def transform_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    new_column_values = marvin.run(
        result_type=list[str],
        instructions="write the word for the sum of the two numbers in the row",
    )
    new_column = pd.Series(
    return df


df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})

