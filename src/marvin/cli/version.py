import platform

from typer import Context, Exit, echo

from marvin import __version__


def display_version(ctx: Context):
    if ctx.resilient_parsing:
        return
    echo(f"Version:\t\t{__version__}")
    echo(f"Python version:\t\t{platform.python_version()}")
    echo(f"OS/Arch:\t\t{platform.system().lower()}/{platform.machine().lower()}")
    raise Exit()
