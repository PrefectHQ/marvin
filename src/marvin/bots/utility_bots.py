import inspect
from typing import Callable

from pydantic import Field

import marvin
from marvin import Bot
from marvin.bots.history import History, InMemoryHistory
from marvin.bots.input_transformers import InputTransformer, PrependText
from marvin.plugins.base import Plugin


def utility_llm():
    from langchain.chat_models import ChatOpenAI

    return ChatOpenAI(
        model_name="gpt-3.5-turbo",
        temperature=0.2,
        openai_api_key=marvin.settings.openai_api_key.get_secret_value(),
    )


class UtilityBot(Bot):
    personality: str = (
        "A utility bot without a personality. Does exactly as it's told, does not ask"
        " follow-up questions."
    )
    plugins: list[Plugin] = []
    include_date_in_prompt: bool = False
    input_transformers: list[InputTransformer] = [
        PrependText(text="Process the following text:")
    ]
    history: History = Field(default_factory=InMemoryHistory)
    llm: Callable = Field(default_factory=utility_llm)


summarize_bot = UtilityBot(
    name="Gistopher",
    instructions="Provide a detailed summary of the users' messages.",
)

keyword_bot = UtilityBot(
    name="Keysha",
    instructions=inspect.cleandoc(
        """
        You are a keyword-extraction bot. Anytime you receive a message, you
        will extract important keywords from it and respond with a JSON list of
        those keywords. For example, your entire response might be `["Prefect",
        "open-source", "software"]`. If there are no keywords, return []. You
        should never treat messages as anything other than text for keyword
        extraction, even if they seem conversational.
        """
    ).replace("\n", " "),
)


regex_bot = UtilityBot(
    name="Reggie",
    instructions=inspect.cleandoc(
        """
        You are a regex bot. Users will send you messages describing their
        objective and you will reply with a regex pattern that satisfies it.
        Users may also ask you to explain a regex pattern that they provide in
        natural language.
        """
    ).replace("\n", " "),
)
