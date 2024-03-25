import logging
import subprocess

log = logging.getLogger("mkdocs")


def on_pre_build(config, **kwargs):
    """Add a custom route to the server."""
    try:
        subprocess.run(
            [
                "npx",
                "tailwindcss",
                "-i",
                "./docs/overrides/tailwind.css",
                "-o",
                "./docs/static/css/tailwind.css",
            ]
        )
    except Exception:
        log.error("You need to install tailwindcss using npx install tailwindcss")
