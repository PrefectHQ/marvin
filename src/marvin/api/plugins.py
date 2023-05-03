from typing import Any

from marvin.plugins.base import Plugin
from marvin.utilities.types import MarvinRouter, get_all_subclasses

router = MarvinRouter(prefix="/plugins", tags=["Plugins"])


@router.get("/")
async def read_plugins() -> dict[str, Any]:
    return {
        plugin.__name__: plugin(description="").dict(json_compatible=True)
        for plugin in get_all_subclasses(Plugin)
        if plugin.__name__ != "Plugin"
    }
