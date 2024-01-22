import asyncio
import inspect
import math

from marvin._rag.vectorstores.tpuf import TurboPuffer, tpuf_settings
from marvin.utilities.strings import slice_tokens


async def query_turbopuffer(query: str, top_k: int = 10, n_tokens: int = 1000) -> str:
    """
    Query the TurboPuffer API for documents related to the given query string.

    Args:
        query (str): The query string to search for.
        top_k (int, optional): The top k results to return. Defaults to 10.

    Returns:
        list[dict]: A list of dictionaries containing the results.
    """

    async with TurboPuffer() as tpuf:
        vector_result = await tpuf.query(text=query, top_k=top_k)

        maybe_documents = tpuf_settings.fetch_document_fn(
            tuple(vec.id for vec in vector_result.data)
        )
        if inspect.isawaitable(maybe_documents):
            documents = await maybe_documents
        else:
            documents = maybe_documents

        return slice_tokens(
            "\n".join([document.text for document in documents]),
            n_tokens=n_tokens,
        )


async def multi_query_turbopuffer(
    queries: list[str], top_k: int = 10, n_tokens: int = 2000
) -> str:
    """
    Query the TurboPuffer API for documents related to the given query strings.

    Args:
        queries (list[str]): The query strings to search for.
        top_k (int, optional): The top k results to return. Defaults to 10.

    Returns:
        A string containing the concatenated results.
    """
    excerpts = await asyncio.gather(
        *[
            query_turbopuffer(
                query=query,
                top_k=math.ceil(top_k / len(queries)),
                n_tokens=n_tokens // len(queries),
            )
            for query in queries
        ]
    )

    return "\n".join(excerpts)
