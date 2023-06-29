from fastapi import FastAPI, APIRouter
import uvicorn
from pydantic import BaseModel, Extra
from typing import TypeVar, Union, Optional
import asyncio
from marvin import AIApplication, AIModel, AIFunction, ai_model
import nest_asyncio

nest_asyncio.apply()

# Define the types
A = TypeVar("A", bound="AIApplication")
B = TypeVar("B", bound="AIModel")
C = TypeVar("C", bound="AIFunction")


class Deployment(BaseModel):
    """
    Deployment class handles the deployment of AI applications, models or functions.
    """

    def __init__(
        self,
        primitive: Union[A, B, C],
        *args,
        app_kwargs: Optional[dict] = None,
        router_kwargs: Optional[dict] = None,
        uvicorn_kwargs: Optional[dict] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._app = FastAPI(**(app_kwargs or {}))
        self._router = APIRouter(**(router_kwargs or {}))
        self._controller = primitive
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

        if issubclass(self._controller.__class__, AIApplication):
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

        if issubclass(self._controller.__class__, AIModel):
            raise NotImplementedError

        if issubclass(self._controller.__class__, AIFunction):
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
