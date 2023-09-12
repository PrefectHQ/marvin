"""
OpenAI Embeddings for Marvin Library
====================================

This module provides utilities for creating embeddings using the OpenAI API 
for the Marvin library.

Main Features:
--------------
- `create_openai_embeddings`: Generates embeddings for a list of texts using OpenAI.

Usage:
------
    embeddings = await create_openai_embeddings(["Hello", "World"])
    print(embeddings)

Note:
-----
This module assumes that the `openai` and `marvin` libraries are properly installed and 
available in the PYTHONPATH. Additionally, the `numpy` library is required for 
creating OpenAI embeddings.

The module leverages `marvin.settings.openai.embedding_engine` to get the 
embedding engine details.
"""

from typing import List

import openai

import marvin


async def create_openai_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Create embeddings for a list of texts using the OpenAI API.

    This function sends the provided texts to the OpenAI API and retrieves their
    embeddings. It requires the `numpy` library to be installed.

    Args:
    - texts (List[str]): List of texts for which embeddings are to be created.

    Returns:
    - List[List[float]]: List of embeddings corresponding to the provided texts.

    Raises:
    - ImportError: If the `numpy` library is not installed.
    """

    try:
        import numpy  # type: ignore # noqa: F401
    except ImportError:
        raise ImportError(
            "The numpy package is required to create OpenAI embeddings. Please install"
            " it with `pip install numpy` or `pip install 'marvin[slackbot]'`."
        )

    # Clean texts by replacing newline characters
    cleaned_texts = [text.replace("\n", " ") for text in texts]

    # Get embeddings from OpenAI
    embeddings = await openai.Embedding.acreate(  # type: ignore
        input=cleaned_texts,
        engine=marvin.settings.openai.embedding_engine,
    )

    # Sort embeddings based on index and return
    return [r["embedding"] for r in sorted(embeddings["data"], key=lambda x: x["index"])]  # type: ignore # noqa: E501
