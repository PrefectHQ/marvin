from datetime import datetime

from marvin.components.ai_function import ai_fn


@ai_fn
def summarize_text(text: str, specifications: str = "concise, comprehensive") -> str:
    """generates a summary of `text` according to the `specifications`"""


@ai_fn
def make_datetime(description: str, tz: str = "UTC") -> datetime:
    """generates a datetime from a description"""
