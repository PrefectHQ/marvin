from typing import Callable

from fastapi.routing import APIRouter


class FunctionRegistry(APIRouter):
    def attach(self, functions: list[Callable], **route_kwargs):
        for function in functions:
            self.add_api_route(
                **{
                    "methods": ["POST"],
                    "path": f"/tools/{function.__name__}",
                    "description": function.__doc__,
                    **route_kwargs,
                    "endpoint": function,
                }
            )
