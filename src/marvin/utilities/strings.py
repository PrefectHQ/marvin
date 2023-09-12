"""
Text Processing and Rendering Utilities
=======================================

This module offers utility functions tailored for tasks such as tokenizing, rendering,
and text manipulation. It is especially designed for:
- Converting text into tokens suitable for models like "gpt-3.5-turbo".
- Rendering nested variables within templates.
- Transitioning between different text formats, e.g., Markdown to Slack-style links.

While the module can be used in diverse contexts, it is primarily designed for 
managing and processing text in applications like vector stores and templating engines.
"""

import inspect
import re
from typing import Any, Optional

import tiktoken
from bs4 import BeautifulSoup
from jinja2 import (
    ChoiceLoader,
    Environment,
    StrictUndefined,
    pass_context,
    select_autoescape,
)
from jinja2.runtime import Context
from markupsafe import Markup

import marvin.utilities.async_utils

NEWLINES_PATTERN = re.compile(r"(\s*\n\s*)")
MD_LINK_PATTERN = re.compile(r"\[(?P<text>[^\]]+)]\((?P<url>[^\)]+)\)")

jinja_env = Environment(
    loader=ChoiceLoader([]),  # Placeholder for potential future loaders
    autoescape=select_autoescape(default_for_string=False),
    trim_blocks=True,
    lstrip_blocks=True,
    auto_reload=True,
    undefined=StrictUndefined,
)

# Update Jinja global functions
jinja_env.globals.update(  # type: ignore
    zip=zip,  # type: ignore
    arun=marvin.utilities.async_utils.run_sync,  # type: ignore
)  #


@pass_context
def _render_nested_variables(context: Context, value: str) -> str:
    """
    Renders nested variables within a string.

    This function facilitates the rendering of nested variables that might contain other
    variables. For instance, in a template with `{{ description | render }}`,
    if `description` contains other Jinja2 placeholders, they will be appropriately
    rendered.

    Args:
    - context: The current Jinja2 context.
    - value (str): The string containing potential nested variables.

    Returns:
    - str: The rendered string with all nested variables resolved.
    """
    template = context.eval_ctx.environment.from_string(value)
    rendered = template.render(**context)
    return Markup(rendered) if context.eval_ctx.autoescape else rendered


jinja_env.filters["render"] = _render_nested_variables  # type: ignore


def tokenize_text(
    text: str,
    model: Optional[str] = None,
) -> list[int]:
    """
    Convert a given text into a list of tokens suitable for the "gpt-3.5-turbo" model.

    Args:
    - text (str): The input text to tokenize.
    - model (Optional[str]): The name of the model to use for tokenization. If None,
                             the default model "gpt-3.5-turbo" is used.

    Returns:
    - list[int]: A list of tokens representing the input text.
    """
    tokenizer = tiktoken.encoding_for_model(model or "gpt-3.5-turbo")
    return tokenizer.encode(text)


def detokenize_text(tokens: list[int]) -> str:
    """
    Convert a list of tokens back into the original text format.

    Args:
    - tokens (list[int]): The input tokens to detokenize.

    Returns:
    - str: The reconstructed text from the tokens.
    """
    tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo")
    return tokenizer.decode(tokens)


def get_token_count(text: str) -> int:
    """
    Count the number of tokens in a given text for the "gpt-3.5-turbo" model.

    Args:
    - text (str): The input text.

    Returns:
    - int: The number of tokens in the text.
    """
    return len(tokenize_text(text))


def truncate_text_by_tokens(text: str, max_tokens: int) -> str:
    """
    Truncate a given text to a specified number of tokens.

    Args:
    - text (str): The input text to truncate.
    - max_tokens (int): The maximum number of tokens the output should have.

    Returns:
    - str: The truncated text.
    """
    tokens = tokenize_text(text)
    return detokenize_text(tokens[:max_tokens])


def split_text_by_token_count(text: str, chunk_size: int) -> list[str]:
    """
    Split a text into chunks, where each chunk has a specified token count or fewer.

    Args:
    - text (str): The input text to split.
    - chunk_size (int): The desired token count for each chunk.

    Returns:
    - list[str]: A list of text chunks.
    """
    tokens = tokenize_text(text)
    return [
        detokenize_text(tokens[i : i + chunk_size])
        for i in range(0, len(tokens), chunk_size)
    ]  # noqa: E501


def normalize_newlines(text: str) -> str:
    """
    Clean and condense consecutive newline characters in a text.

    This function ensures that the text does not have unnecessary spaces or consecutive
    newline characters. It's especially useful for cleaning up multi-line strings or
    text extracted from various sources.

    Args:
    - text (str): The input text with potential excessive newlines.

    Returns:
    - str: The cleaned-up text.
    """

    def replace_whitespace(match: re.Match[Any]) -> str:
        newline_count = match.group().count("\n")
        return "\n" * newline_count if newline_count > 1 else " "

    text = inspect.cleandoc(text)
    return NEWLINES_PATTERN.sub(replace_whitespace, text).strip()


def extract_text_from_html(html: str) -> str:
    """
    Extract and clean the textual content from an HTML string.

    This function removes any scripts, styles, and HTML tags, leaving only the
    textual content. It's useful for extracting readable content from web pages
    or other HTML sources.

    Args:
    - html (str): The input HTML string.

    Returns:
    - str: The extracted text.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.extract()

    return normalize_newlines(soup.get_text())


def convert_markdown_links_to_slack(text: str) -> str:
    """
    Convert Markdown-style links to Slack's link format.

    For example, the Markdown link `[OpenAI](https://openai.com)`
    would be converted to Slack format as `<https://openai.com|OpenAI>`.

    Args:
    - text (str): The input text containing Markdown-style links.

    Returns:
    - str: The text with links converted to Slack format.
    """

    def markdown_to_slack_link(match: re.Match[Any]) -> str:
        return f'<{match.group("url")}|{match.group("text")}>'

    return MD_LINK_PATTERN.sub(markdown_to_slack_link, text)


# ------------------
# Deprecated aliases
# ------------------

count_tokens = get_token_count
