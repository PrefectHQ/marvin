from typing import TYPE_CHECKING

from marvin.ai_functions import ai_fn

if TYPE_CHECKING:
    from pandas import DataFrame


@ai_fn
def map_categories(data: list[str], categories: list[str]) -> list[str]:
    """
    Assign each item in `data` to the value in `categories` that it matches most
    closely. For example, if the data is ["apple", "carrot", "banana",
    "broccoli"] and the categories are ["fruit", "vegetable"], then the result
    would be ["fruit", "vegetable", "fruit", "vegetable"]. If the categories
    were ["a", "b", "c", "d"] then the result would be ["a", "c", "b", "b"].
    """


@ai_fn
def categorize(data: list[str], description: str) -> list[str]:
    """
    Given a `description` of some possible categories, map each item in `data`
    to the most relevant category. For example, if the description is "pets",
    valid categories would be "cat", "dog", "fish", etc. If the description is
    "airports (JFK, etc.)" then valid categories would be "LGA", "LAX", "IAD",
    etc. Return a list of assigned categories the same length and order as
    `data`.
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


@ai_fn(llm_model="gpt-3.5-turbo", temperature=0)
def summarize(text: str, tone: str = "conversational agent") -> str:
    """
    Given a block of text, return a summary of the text in the given tone.
    """
