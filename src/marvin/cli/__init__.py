import typer

from .manage import app as manage
from .admin import app as admin

app = typer.Typer()
app.add_typer(manage, name="manage")
app.add_typer(admin, name="admin")

if __name__ == "__main__":
    app()
