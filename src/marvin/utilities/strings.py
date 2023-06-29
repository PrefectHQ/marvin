import asyncio
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
    arun=asyncio.run,
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
    tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo-0613")
    return tokenizer.encode(text)


def detokenize(tokens: list[int]) -> str:
    tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo-0613")
    return tokenizer.decode(tokens)


def count_tokens(text: str) -> int:
    return len(tokenize(text))


def slice_tokens(text: str, n_tokens: int) -> str:
    tokens = tokenize(text)
    return detokenize(tokens[:n_tokens])


def convert_md_links_to_slack(text):
    md_link_pattern = r"\[(?P<text>[^\]]+)]\((?P<url>[^\)]+)\)"

    # converting Markdown links to Slack-style links
    def to_slack_link(match):
        return f'<{match.group("url")}|{match.group("text")}>'

    # Replace Markdown links with Slack-style links
    slack_text = re.sub(md_link_pattern, to_slack_link, text)

    return slack_text
