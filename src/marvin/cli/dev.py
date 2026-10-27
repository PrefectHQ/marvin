import subprocess
from pathlib import Path

import typer

dev_app = typer.Typer(no_args_is_help=True)


@dev_app.command()
def docs():
    """Run the Marvin documentation locally. Equivalent to 'cd docs && npx mint dev' from the Marvin root."""
    try:
        # Get the absolute path of the Marvin main repo
        repo_root = Path(__file__).resolve().parents[3]
        docs_path = repo_root / "docs"

        if not docs_path.exists():
            typer.echo(f"Error: Docs directory not found at {docs_path}", err=True)
            raise typer.Exit(code=1)

        typer.echo(f"Changing directory to: {docs_path}")

        typer.echo("Running 'npx mint dev'...")
        subprocess.run(["npx", "mint", "dev"], cwd=docs_path, check=True)

    except subprocess.CalledProcessError as e:
        typer.echo(f"Error running 'npx mint dev': {e!s}", err=True)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.echo(f"An error occurred: {e!s}", err=True)
        raise typer.Exit(code=1)
