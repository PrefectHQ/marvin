from .typer import AsyncTyper

from .manage import app as manage
from .admin import app as admin
from .chat import chat

app = AsyncTyper()

app.add_typer(manage, name="manage")
app.add_typer(admin, name="admin")

app.acommand()(chat)


if __name__ == "__main__":
    app()
