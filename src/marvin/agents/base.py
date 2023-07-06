from typing import Callable

from fastapi import FastAPI
from fastapi.routing import APIRouter
from marvin.engine.executors import Executor, OpenAIExecutor
from marvin.engine.language_models import ChatLLM
from marvin.functions.base import FunctionRegistry
from marvin.prompts import Prompt
from pydantic import BaseModel, Extra


class Agent(
    BaseModel, allow_mutation=True, extra=Extra.allow, arbitrary_types_allowed=True
):
    name: str
    engine: ChatLLM = ChatLLM()
    prompts: list[Prompt] = []
    functions: list[Callable] = []

    _app: FastAPI = FastAPI()
    _flow: Executor = OpenAIExecutor
    _router: APIRouter = APIRouter
    _function_registry: FunctionRegistry = FunctionRegistry

    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)
        self._router = APIRouter()
        self._function_registry = FunctionRegistry()
        self._router.prefix = f"/{self.name}"
        self._router.get("/")(self.call)
        self._function_registry.attach(functions=self.functions)

    def __call__(self, path: str = "/", *args, **kwargs):
        return self._function_registry.routes

    @property
    def router(self):
        self._router.include_router(self._function_registry)
        return self._router

    @property
    def app(self):
        self._app.include_router(self.router)
        return self._app

    async def call(self, q: str) -> str:
        response = await self._flow(
            engine=self.engine,
            functions=[route.endpoint for route in self._function_registry.routes],
        ).start(q)
        return response[-1].content

    def register(self, *args, **kwargs):
        def decorator(func):
            def wrapper(*tool):
                return func(*tool)

            existing_function_names = [
                route.endpoint.__name__ for route in self._function_registry.routes
            ]
            if func.__name__ not in existing_function_names:
                self._function_registry.attach(functions=[func], **kwargs)
                self.functions = [
                    route.endpoint for route in self._function_registry.routes
                ]

            return wrapper

        return decorator
