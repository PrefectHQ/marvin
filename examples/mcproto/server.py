# /// script
# dependencies = ["mcp", "atproto"]
# ///

import asyncio
import contextlib
import hashlib
import warnings
from datetime import datetime
from typing import Iterator

from atproto import Client, models
from mcp.server.fastmcp import FastMCP
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", env_prefix="BSKY_"
    )

    handle: str | None = None
    password: str | None = None


@contextlib.contextmanager
def register_mcp_server_with_atproto(
    server: FastMCP,
    *,
    name: str,
    package: str,
    description: str | None = None,
    version: str = "1.0.0",
) -> Iterator[FastMCP]:
    """Context manager to register an MCP server with ATProto if credentials exist.

    Example:
        mcp = FastMCP("My Server")

        @mcp.tool()
        def my_tool():
            ...

        with register_mcp_server_with_atproto(
            mcp,
            name="My Server",
            package="https://github.com/me/repo/blob/main/server.py",
            description="Does cool stuff"
        ):
            mcp.run()
    """
    settings = Settings()

    if settings.handle and settings.password:
        try:
            client = Client()
            profile = client.login(settings.handle, settings.password)

            # Get list of tools from server
            tools = [tool.name for tool in asyncio.run(server.list_tools())]

            # Check for existing record with same package URL
            existing_records = client.com.atproto.repo.list_records(
                params=models.ComAtprotoRepoListRecords.Params(
                    repo=profile.did,
                    collection="app.mcp.server",
                ),
            )

            # Create a valid record key from package URL
            # Must be 1-512 chars of ASCII without whitespace or control chars
            def make_valid_rkey(package: str) -> str:
                # Create a deterministic but valid rkey from package URL
                # Hash it to ensure valid chars and reasonable length
                h = hashlib.sha256(package.encode()).hexdigest()[:32]
                # Ensure starts with a letter (ATProto requirement)
                return f"k{h}"

            rkey = make_valid_rkey(package)

            # Find existing record by rkey
            existing_record = None
            for record in existing_records.records:
                if record.uri.split("/")[-1] == rkey:
                    existing_record = record
                    break

            # Prepare record data
            record_content = {
                "type": "app.mcp.server",
                "name": name,
                "package": package,
                "version": version,
                "description": description,
                "tools": tools,
                "createdAt": (
                    existing_record.value["createdAt"]
                    if existing_record and isinstance(existing_record.value, dict)
                    else datetime.now().isoformat()
                ),
                "lastRegisteredAt": datetime.now().isoformat(),
            }

            if existing_record:
                # Update existing record
                client.com.atproto.repo.put_record(
                    data=models.ComAtprotoRepoPutRecord.Data(
                        repo=profile.did,
                        collection="app.mcp.server",
                        rkey=rkey,
                        record=record_content,
                    )
                )
            else:
                # Create new record with stable rkey
                client.com.atproto.repo.create_record(
                    models.ComAtprotoRepoCreateRecord.Data(
                        repo=profile.did,
                        collection="app.mcp.server",
                        rkey=rkey,  # Use stable rkey
                        record=record_content,
                    )
                )

        except Exception as e:
            warnings.warn(f"Failed to register MCP server with ATProto: {e}")
    else:
        warnings.warn(
            "BSKY_HANDLE and BSKY_PASSWORD environment variables not set. "
            "Server will run but won't be registered with ATProto."
        )

    yield server


if __name__ == "__main__":
    mcp = FastMCP("Example Server")

    @mcp.tool()
    def echo(message: str) -> str:
        """Echo back the input message."""
        return f"Echo: {message}"

    @mcp.tool()
    def add(a: float, b: float) -> str:
        """Add two numbers."""
        return f"The sum of {a} and {b} is {a + b}."

    with register_mcp_server_with_atproto(
        mcp,
        name="Example Server",
        package="https://github.com/prefecthq/marvin/blob/main/examples/mcproto/server.py",
        description="A simple example MCP server",
    ):
        mcp.run()
