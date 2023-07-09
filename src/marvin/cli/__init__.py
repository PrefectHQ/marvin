from .typer import AsyncTyper

from .admin import app as admin
from .chat import chat

app = AsyncTyper()

app.add_typer(admin, name="admin")

app.acommand()(chat)


if __name__ == "__main__":
    app()
