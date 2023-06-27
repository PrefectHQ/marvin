from typing import Any, Callable, List, Type, Union

from fastapi import APIRouter
from fastapi.routing import APIRouter
from marvin.engines.language_models import ChatLLM
from marvin.prompts import Prompt, System, User
from pydantic import BaseModel, Extra, root_validator, validator


class FunctionRegistry(APIRouter):
    def attach(self, functions: list[Callable], **kwargs):
        for function in functions:
            self.add_api_route(**{
                'methods': ['POST'],
                'path': f'/tools/{function.__name__}',
                'description': function.__doc__,
                **kwargs,
                'endpoint': function
            })
        
class Agent(BaseModel, 
    allow_mutation = True, 
    extra = Extra.allow, 
    arbitrary_types_allowed = True
):
    engine: ChatLLM = ChatLLM()
    prompts: list[Prompt] = []
    functions: list[Callable] = []
    
    _router: APIRouter = APIRouter()
    _function_registry: FunctionRegistry = FunctionRegistry()
        
    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)
        self._function_registry.attach(functions = self.functions)
        
    @property
    def router(self):
        self._router.include_router(self._function_registry)
        return(self._router)
    
    def register(self, *args, **kwargs):
        def decorator(func):
            def wrapper(*tool):
                return func(*tool) 
            self._function_registry.attach(functions = [func], **kwargs)
            self.functions = [route.endpoint for route in self._function_registry.routes]
            return wrapper
        return decorator