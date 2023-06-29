import asyncio
from typing import Union, Optional

import uvicorn
from fastapi import FastAPI, APIRouter
from pydantic import BaseModel, Extra

from marvin import AIApplication, AIModel, AIFunction


class Deployment(BaseModel):
    """
    Deployment class handles the deployment of AI applications, models or functions.
    """

    def __init__(
        self,
        component: Union[AIApplication, AIModel, AIFunction],
        *args,
        app_kwargs: Optional[dict] = None,
        router_kwargs: Optional[dict] = None,
        uvicorn_kwargs: Optional[dict] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._app = FastAPI(**(app_kwargs or {}))
        self._router = APIRouter(**(router_kwargs or {}))
        self._controller = component
        self._mount_router()
        self._uvicorn_kwargs = {
            "app": self._app,
            "host": "0.0.0.0",
            "port": 8000,
            **(uvicorn_kwargs or {}),
        }

    def _mount_router(self):
        """
        Mounts a router to the FastAPI app for each tool in the AI application.
        """

        if isinstance(self._controller, AIApplication):
            name = self._controller.name
            base_path = f"/{name.lower()}"
            self._router.get(base_path, tags=[name])(self._controller.entrypoint)
            for tool in self._controller.tools:
                if tool.fn:
                    tool_path = f"{base_path}/tools/{tool.name}"
                    self._router.post(tool_path, tags=[name])(tool.fn)
            self._app.include_router(self._router)
            self._app.openapi_tags = self._app.openapi_tags or []
            self._app.openapi_tags.append(
                {"name": name, "description": self._controller.description}
            )

        if isinstance(self._controller, AIModel):
            raise NotImplementedError

        if isinstance(self._controller, AIFunction):
            raise NotImplementedError

    def serve(self):
        """
        Serves the FastAPI app.
        """
        try:
            config = uvicorn.Config(**(self._uvicorn_kwargs or {}))
            server = uvicorn.Server(config)
            loop = asyncio.get_event_loop()
            loop.run_until_complete(server.serve())
        except Exception as e:
            print(f"Error while serving the application: {e}")

    class Config:
        extra = Extra.allow
