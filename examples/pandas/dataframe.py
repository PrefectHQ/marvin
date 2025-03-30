"""
fills out a new column in a dataframe, adding values to many columns concurrently
"""

import sys
from pathlib import Path
from typing import Annotated

import numpy
import pandas as pd
from prefect import flow, task
from prefect.cache_policies import INPUTS, CacheKeyFnPolicy
from pydantic import Field

import marvin

ColumnValue = Annotated[str, Field(description="UPPERCASE", max_length=15)]

INPUTS_and_FILE_MODIFIED = INPUTS + CacheKeyFnPolicy(
    cache_key_fn=lambda _, parameters: str(
        Path(p).stat().st_mtime
        if not (p := parameters["df_path"]).startswith("http")
        else None
    )
)


@task(cache_policy=INPUTS_and_FILE_MODIFIED)
def read_csv(df_path: str, max_rows: int) -> pd.DataFrame:
    return pd.read_csv(df_path).head(max_rows)


@task
def add_columns_to_dataframe(
    df: pd.DataFrame, new_column_names: list[str]
) -> pd.DataFrame:
    new_column_values = (
        task(marvin.run)
        .map(
            result_type=ColumnValue,
            instructions="select the most plausibly correct value for the new column",
            context=[
                {
                    "column_name": column_name,
                    "existing_row": row[1].to_dict(),
                }
                for column_name in new_column_names
                for row in df.iterrows()
            ],
        )
        .result()
    )
    df.loc[:, new_column_names] = numpy.array(new_column_values).reshape(-1, len(df)).T
    return df


@task
def display_df(df: pd.DataFrame) -> None:
    print(f"\n\n{df}\n\n")


@flow(
    log_prints=True,
    flow_run_name="add columns: {new_column_names} to dataframe from {df_path}",
)
def sketchy_etl(new_column_names: list[str], df_path: str, max_rows: int = 10):
    raw_df = read_csv(df_path, max_rows)
    df = add_columns_to_dataframe(raw_df, new_column_names)
    display_df(df, wait_for=[df])


if __name__ == "__main__":
    """
    uv run examples/dataframe.py <new_column_names> <df_csv_path>

    example:
        >> uv run examples/dataframe.py hometown,age,gender path/to/dataframe.csv
    """
    new_column_names = (
        sys.argv[1] if len(sys.argv) > 1 else "known for,birth year"
    ).split(",")

    df_path = (
        sys.argv[2] if len(sys.argv) > 2 else str(Path(__file__).parent / "data.csv")
    )
    sketchy_etl(new_column_names, df_path)
