import typer
import os
import shutil
from jinja2 import Template

from pathlib import Path
from marvin.cli.admin.scripts.create_env_file import create_env_file
from marvin.cli.admin.scripts.create_secure_key import create_secure_key
from marvin._framework._defaults import default_settings

# Get the absolute path of the current file
filename = Path(__file__).resolve()

# Navigate two directories back from the current file
source_path = filename.parent.parent.parent / "_framework"

app = typer.Typer()


@app.command()
def startproject(no_input: bool = False):
    project_name = typer.prompt("Project Name")
    openai_api_key = typer.prompt("OpenAI API Key")
    shutil.copytree(
        source_path,
        os.path.join(os.getcwd(), project_name),
        ignore=shutil.ignore_patterns(
            "@*"
        ),  # This will ignore all files/directories starting with @
    )
    with open(
        os.path.join(os.getcwd(), project_name, "config/settings.py"), "r"
    ) as file:
        template = Template(file.read())
        rendered = template.render(
            **default_settings, project_name=project_name, openai_api_key=openai_api_key
        )
    with open(
        os.path.join(os.getcwd(), project_name, "config/settings.py"), "w"
    ) as rendered_file:
        rendered_file.write(rendered)
    create_env_file(
        os.path.join(os.getcwd(), project_name),
        [("MARVIN_SECRET", create_secure_key()), ("OPENAI_API_KEY", openai_api_key)],
    )


@app.command()
def startapp(no_input: bool = False):
    print("beep")


if __name__ == "__main__":
    app()
