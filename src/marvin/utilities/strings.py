import inspect
import re
from datetime import datetime
from zoneinfo import ZoneInfo

import tiktoken
from jinja2 import (
    ChoiceLoader,
    Environment,
    StrictUndefined,
    pass_context,
    select_autoescape,
)
from markupsafe import Markup

import marvin.utilities.async_utils

NEWLINES_REGEX = re.compile(r"(\s*\n\s*)")
MD_LINK_REGEX = r"\[(?P<text>[^\]]+)]\((?P<url>[^\)]+)\)"

jinja_env = Environment(
    loader=ChoiceLoader(
        [
            # PackageLoader("marvin", "prompts")
        ]
    ),
    autoescape=select_autoescape(default_for_string=False),
    trim_blocks=True,
    lstrip_blocks=True,
    auto_reload=True,
    undefined=StrictUndefined,
)

jinja_env.globals.update(
    zip=zip,
    arun=marvin.utilities.async_utils.run_sync,
    now=lambda: datetime.now(ZoneInfo("UTC")),
)


@pass_context
def render_filter(context, value):
    """
    Allows nested rendering of variables that may contain variables themselves
    e.g. {{ description | render }}
    """
    _template = context.eval_ctx.environment.from_string(value)
    result = _template.render(**context)
    if context.eval_ctx.autoescape:
        result = Markup(result)
    return result


jinja_env.filters["render"] = render_filter


def tokenize(text: str) -> list[int]:
    tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo")
    return tokenizer.encode(text)


def detokenize(tokens: list[int]) -> str:
    tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo")
    return tokenizer.decode(tokens)


def count_tokens(text: str) -> int:
    return len(tokenize(text))


def slice_tokens(text: str, n_tokens: int) -> str:
    tokens = tokenize(text)
    return detokenize(tokens[:n_tokens])


def split_tokens(text: str, n_tokens: int) -> list[str]:
    tokens = tokenize(text)
    return [
        detokenize(tokens[i : i + n_tokens]) for i in range(0, len(tokens), n_tokens)
    ]


def condense_newlines(text: str) -> str:
    def replace_whitespace(match):
        newlines_count = match.group().count("\n")
        if newlines_count <= 1:
            return " "
        else:
            return "\n" * newlines_count

    text = inspect.cleandoc(text)
    text = NEWLINES_REGEX.sub(replace_whitespace, text)
    return text.strip()


def html_to_content(html: str) -> str:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")

    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.extract()

    # Get text
    text = soup.get_text()

    # Condense newlines
    return condense_newlines(text)


def convert_md_links_to_slack(text) -> str:
    # converting Markdown links to Slack-style links
    def to_slack_link(match):
        return f'<{match.group("url")}|{match.group("text")}>'

    # Replace Markdown links with Slack-style links
    slack_text = re.sub(MD_LINK_REGEX, to_slack_link, text)

    return slack_text
