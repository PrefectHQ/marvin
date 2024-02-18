"""Utilities for working with OpenAI."""

import asyncio
import inspect
from functools import lru_cache
from typing import Any, Optional, Union

from openai import AsyncAzureOpenAI, AsyncClient, AzureOpenAI, Client

import marvin


def get_openai_client(
    is_async: bool = True,
) -> Union[AsyncClient, Client, AzureOpenAI, AsyncAzureOpenAI]:
    """
    Retrieves an OpenAI client (sync or async) based on the current configuration.

    Returns:
        The OpenAI client

    Example:
        Retrieving an OpenAI client
        ```python
        from marvin.utilities.openai import get_client

        client = get_client()
        ```
    """

    kwargs = {}

    # --- Openai
    if marvin.settings.provider == "openai":
        client_class = AsyncClient if is_async else Client

        api_key = (
            marvin.settings.openai.api_key.get_secret_value()
            if marvin.settings.openai.api_key
            else None
        )

        if not api_key:
            raise ValueError(
                inspect.cleandoc(
                    """
                    OpenAI API key not found! Marvin will not work properly without it.
                    
                    You can either:
                        1. Set the `MARVIN_OPENAI_API_KEY` or `OPENAI_API_KEY` environment variables
                        2. Set `marvin.settings.openai.api_key` in your code (not recommended for production)
                        
                    If you do not have an OpenAI API key, you can create one at https://platform.openai.com/api-keys.
                    """
                )
            )

        kwargs.update(
            api_key=api_key,
            organization=marvin.settings.openai.organization,
            base_url=marvin.settings.openai.base_url,
        )

    # --- Azure OpenAI
    elif marvin.settings.provider == "azure_openai":
        api_key = getattr(marvin.settings, "marvin_azure_openai_api_key", None)
        api_version = getattr(marvin.settings, "marvin_azure_openai_api_version", None)
        azure_endpoint = getattr(marvin.settings, "marvin_azure_openai_endpoint", None)

        if any(k is None for k in [api_key, api_version, azure_endpoint]):
            raise ValueError(
                inspect.cleandoc(
                    """
                Azure OpenAI configuration is missing. Marvin will not work properly without it.
                
                Please make sure to set the following environment variables:
                    - MARVIN_AZURE_OPENAI_API_KEY
                    - MARVIN_AZURE_OPENAI_API_VERSION
                    - MARVIN_AZURE_OPENAI_ENDPOINT
                    
                In addition, you must set the LLM model name to your Azure OpenAI deployment name, e.g.
                    - MARVIN_CHAT_COMPLETIONS_MODEL = <your Azure OpenAI deployment name>
                """
                )
            )
        client_class = AsyncAzureOpenAI if is_async else AzureOpenAI
        kwargs.update(
            api_key=api_key,
            api_version=api_version,
            azure_endpoint=azure_endpoint,
        )

    # --- N/A
    else:
        raise ValueError(f"Unknown provider {marvin.settings.provider}")

    loop = asyncio.get_event_loop() if is_async else None

    return _get_client_memoized(
        cls=client_class,
        loop=loop,
        kwargs_items=tuple(kwargs.items()),
    )


@lru_cache
def _get_client_memoized(
    cls: type,
    loop: Optional[asyncio.AbstractEventLoop] = None,
    kwargs_items: tuple[tuple[str, Any]] = None,
) -> Union[Client, AsyncClient]:
    """
    This function is memoized to ensure that only one instance of the client is
    created for a given set of configuration parameters

    It can return either a sync or an async client.

    The `loop` is an important key to ensure that the client is not re-used
    across multiple event loops (which can happen when using the `run_sync`
    function). Attempting to re-use the client across multiple event loops
    can result in a `RuntimeError: Event loop is closed` error or infinite hangs.

    kwargs_items is a tuple of dict items to get around the fact that
    memoization requires hashable arguments.
    """
    return cls(**dict(kwargs_items))
