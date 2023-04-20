from typing import TYPE_CHECKING

from marvin import ai_fn

if TYPE_CHECKING:
    from pandas import DataFrame


@ai_fn
def map_categories(data: list[str], categories: list[str]) -> list[str]:
    """
    Assign each item in `data` to the value in `categories` that it matches most
    closely. Every item must be assigned to a category. Do not assign a `null`
    cateogry.
    """


@ai_fn
def categorize(data: list[str], description: str) -> list[str]:
    """
    Map each item in `data` to a value that matches the `description`
    as close as possible. For example, if the description is "pets",
    valid categories would be "cat", "dog", "fish", etc. The category
    description may include examples. Return a list of assigned categories the
    same length and order as `data`.
    """


@ai_fn
def context_aware_fillna(data: list[list], columns: list[str] = None) -> list[list]:
    """
    Given data organized as a list of rows, where each row is a list of values,
    and some missing values (either `None` or `np.nan`), fill in any missing
    values based on other data in the same row. Use the `columns` names and
    other data to understand the likely data model. Returns the original data
    with the missing values filled in.
    """


def context_aware_fillna_df(data: "DataFrame") -> "DataFrame":
    """
    Given a dataframe  with some missing values (either `None` or `np.nan`),
    fill in any missing values based on other data in the same row.
    """
    try:
        import pandas as pd
    except ImportError:
        raise ImportError("context_aware_fillna_df requires pandas to be installed")
    clean_data = context_aware_fillna(
        data=data.values.tolist(), columns=data.columns.to_list()
    )
    return pd.DataFrame(clean_data, columns=data.columns.to_list())


@ai_fn
def standardize(data: list[str], format: str) -> list[str]:
    """
    Given a list of data, standardize the data to the given format. For example,
    the format could be "phone number", "sentence case", "ISO date", etc.
    """
