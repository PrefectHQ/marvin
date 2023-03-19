import asyncio
import socket

import anyio
import httpx
import marvin
import marvin.server
import pytest
import uvicorn


@pytest.fixture()
async def client():
    """
    A client for testing the API.

    This uses the httpx AsyncClient and the ASGI app itself, which can make it
    easier to debug issues (with nicer tracebacks!) but does not support async
    operations like streaming responses. Background tasks have ambiguous
    support; they may run synchronously.
    """
    async with httpx.AsyncClient(
        app=marvin.server.app, base_url="http://test"
    ) as client:
        yield client


@pytest.fixture()
async def streaming_client(server):
    """
    A client for testing the API.

    This client runs against a uvicorn server and represents a "real" client
    better than one that loads the ASGI application itself. In particular, it
    supports streaming data and background tasks. However, it doesn't produce as
    useful tracebacks when testing.
    """
    async with httpx.AsyncClient(
        base_url=f"http://localhost:{server.config.port}"
    ) as client:
        yield client


@pytest.fixture()
def server_port():
    # find a random unused port
    sock = socket.socket()
    sock.bind(("", 0))
    port = sock.getsockname()[1]
    return port


@pytest.fixture()
async def server(server_port):
    """Run the server in a separate thread."""

    config = uvicorn.Config("marvin.server:app", port=server_port)
    server = uvicorn.Server(config)
    # start serving
    task = asyncio.ensure_future(server.serve())

    yield server

    # set flag for graceful shutdown
    server.should_exit = True
    # wait for the server to stop
    with anyio.fail_after(1):
        await task
