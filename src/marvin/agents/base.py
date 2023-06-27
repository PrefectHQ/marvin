from typing import Callable

from fastapi import FastAPI
from fastapi.routing import APIRouter
from marvin.engines.language_models import ChatLLM
from marvin.prompts import Prompt
from pydantic import BaseModel, Extra


class FunctionRegistry(APIRouter):
    def attach(self, functions: list[Callable], **route_kwargs):
        for function in functions:
            self.add_api_route(**{
                'methods': ['POST'],
                'path': f'/tools/{function.__name__}',
                'description': function.__doc__,
                **route_kwargs,
                'endpoint': function
            })
        
class Agent(
    BaseModel, 
    allow_mutation = True, 
    extra = Extra.allow, 
    arbitrary_types_allowed = True
):
    name: str
    engine: ChatLLM = ChatLLM()
    prompts: list[Prompt] = []
    functions: list[Callable] = []
    
    _app: FastAPI = FastAPI()
    _router: APIRouter = APIRouter()
    _function_registry: FunctionRegistry = FunctionRegistry()
        
    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)
        self._router.prefix = self.name
        self._function_registry.attach(functions = self.functions)
        
    def __call__(self, path: str = '/', *args, **kwargs):
        return(self._function_registry.routes)
        
    @property
    def router(self):
        self._router.include_router(self._function_registry)
        return(self._router)
    
    @property
    def app(self):
        self._app.include_router(self.router)
        return(self._app)
    
    def register(self, *args, **kwargs):
        def decorator(func):
            def wrapper(*tool):
                return func(*tool) 
            self._function_registry.attach(functions = [func], **kwargs)
            self.functions = [route.endpoint for route in self._function_registry.routes]
            return wrapper
        return decorator
    