from .typer import AsyncTyper

from .admin import app as admin
from .chat import chat

app = AsyncTyper()

app.add_typer(admin, name="admin")

app.acommand()(chat)


@app.command()
def version():
    import platform
    import sys
    from marvin import __version__

    print(f"Version:\t\t{__version__}")

    print(f"Python version:\t\t{sys.version.split()[0]}")

    print(f"OS/Arch:\t\t{platform.system().lower()}/{platform.machine().lower()}")


if __name__ == "__main__":
    app()
