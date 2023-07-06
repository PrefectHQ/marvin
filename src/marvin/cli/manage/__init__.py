import typer
import subprocess
from marvin.cli.manage.scripts.get_settings import get_settings

app = typer.Typer()


@app.command()
def runserver():
    config = get_settings()
    subprocess.run(["uvicorn", f"{config.asgi}", "--reload"])


if __name__ == "__main__":
    app()
