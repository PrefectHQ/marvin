from typing import Any, Callable, Optional

import pendulum
from pydantic import Field

from marvin.infra.chroma import Chroma
from marvin.plugins import Plugin, plugin
from marvin.utilities.strings import extract_keywords


def build_metadata_filter(where: dict, operator: str = "$and") -> dict:
    filters = []
    for key, value in where.items():
        if key == "created_at":
            filters.append(
                {
                    "created_at": {
                        k: pendulum.parse(v).timestamp() for k, v in value.items()
                    }
                }
            )
        else:
            filters.append({key: value})

    if len(filters) == 1:
        return filters[0]
    return {operator: filters}


def build_keyword_filter(keywords: list[str]) -> dict:
    filters = [{"$contains": keyword} for keyword in keywords]
    return {"$or": filters}


async def query_chroma(**query_kwargs) -> str:
    async with Chroma() as chroma:
        query_result = await chroma.query(**query_kwargs)

    return "\n\n".join(
        excerpt for excerpts in query_result["documents"] for excerpt in excerpts
    )


async def keyword_query_chroma(query: str, where: dict, n: int = 4) -> str:
    keywords = await extract_keywords(query)

    query_kwargs = dict(
        query_texts=[query],
        n_results=n,
        include=["documents"],
        where=build_metadata_filter(where) if where else None,
        where_document=build_keyword_filter(keywords) if keywords else None,
    )

    return await query_chroma(**query_kwargs)


class SimpleChromaSearch(Plugin):
    name: str = "simple-chroma-search"
    description: str = (
        "Semantic search for relevant documents."
        " To use this plugin, simply provide a natural language `query`"
        " and relevant document excerpts will be returned to you."
    )

    keywords: list[str] = Field(default_factory=list)

    def get_full_description(self) -> str:
        base_description = super().get_full_description()
        if self.keywords:
            return (
                base_description
                + " Useful for answering questions that refer to the following"
                " keywords:"
                f" {', '.join(self.keywords)}"
            )
        return base_description

    async def run(self, query: str) -> str:
        return await keyword_query_chroma(query, where=None)


""" --- decorator plugin definition ---

The below plugin allows the LLM to provide both the `where` and `where_document` args
based on the `query` argument. The `where` argument is used to filter the metadata
associated with a document, while the `where_document` argument is used to filter the
actual document text.

Best with GPT-4.

"""


def apply_fn_to_field(data: dict, field: str, visit_fn: Callable) -> dict:
    for key, value in data.items():
        if key == field:
            data[key] = visit_fn(value)
        elif isinstance(value, dict):
            data[key] = apply_fn_to_field(value, field, visit_fn)
        elif isinstance(value, list):
            for i, item in enumerate(value):
                if isinstance(item, dict):
                    value[i] = apply_fn_to_field(item, field, visit_fn)
    return data


def iso_to_timestamp(filter: dict) -> float:
    return {k: pendulum.parse(v).timestamp() for k, v in filter.items()}


@plugin
async def chroma_search(
    query: str,
    where: Optional[dict[str, Any]] = None,
    where_document: Optional[dict[str, Any]] = None,
) -> str:
    """
    query (str): A verbose natural language query.
    where (dict): A dictionary of filters to refine a search. Valid operators
        are `$eq`, `$ne`, `$gt`, `$gte`, `$lt`, `$lte`. For example, to filter
        for info after Feb 1 2017, include "created_at" --> "$gte": "2017-02-01".
        You may `$and` or `$or` a list of many such filters together, and only
        one metadata field can be present in a single filter.
    where_document (dict): A dictionary to filter search results by keywords.
        The only valid operator is `$contains`. For example, to find documents
        containing the word "python", use "$contains" --> "python". You may `$and`
        or `$or` multiple such filters together, the operator being the outer key.
    """

    where = apply_fn_to_field(where, "created_at", iso_to_timestamp) if where else None

    return await query_chroma(
        query_texts=[query],
        n_results=4,
        include=["documents"],
        where=where,
        where_document=where_document if where_document else None,
    )
