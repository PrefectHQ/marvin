from typing import List

import openai

import marvin


async def create_openai_embeddings(texts: List[str]) -> List[List[float]]:
    """Create OpenAI embeddings for a list of texts."""

    try:
        import numpy  # noqa F401
    except ImportError:
        raise ImportError(
            "The numpy package is required to create OpenAI embeddings. Please install"
            " it with `pip install numpy` or `pip install 'marvin[slackbot]'`."
        )

    embeddings = await openai.Embedding.acreate(
        input=[text.replace("\n", " ") for text in texts],
        engine=marvin.settings.openai.embedding_engine,
    )

    return [
        r["embedding"] for r in sorted(embeddings["data"], key=lambda x: x["index"])
    ]
