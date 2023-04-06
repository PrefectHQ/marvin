import typer
import uvicorn

import marvin

server_app = typer.Typer(help="Server commands")


@server_app.command()
def start(
    port: int = typer.Option(
        marvin.settings.api_port,
        "--port",
        "-p",
        help="Port to run the server on",
    ),
    reload: bool = typer.Option(
        marvin.settings.api_reload, "--reload", help="Reload the server on code changes"
    ),
    log_level: str = typer.Option(
        marvin.settings.log_level, "--log-level", "-l", help="Log level for the server"
    ),
):
    uvicorn.run(
        "marvin.server:app", port=port, log_level=log_level.lower(), reload=reload
    )
