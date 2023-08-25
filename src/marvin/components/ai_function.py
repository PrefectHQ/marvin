import asyncio
import functools
import inspect
from typing import Any, Callable, Optional, TypeVar

from jinja2 import Template
from typing_extensions import ParamSpec

from marvin.core.ChatCompletion import ChatCompletion
from marvin.pydantic import BaseModel, Field
from marvin.types import Function, FunctionRegistry

T = TypeVar("T")


P = ParamSpec("P")

system_prompt = inspect.cleandoc("""
        {{ instructions if instructions }}
        
        Your job is to generate likely outputs for a Python function with the
        following signature and docstring:
    
        {{ function_def }}        
        
        The user will provide function inputs (if any) and you must respond with
        the most likely result. 
        
        {% if description %}
        The following function description was also provided:

        {{ description }}
        {% endif %}
        {% if functions|length > 1 %}
        You may call any provided function as necessary, but before any final 
        response is returned to the user you must format your response using 
        the {{functions[0].__name__}} function.
        {% endif %}
        """)

user_prompt = inspect.cleandoc("""\
        {% if input_binds %} 
        The function was called with the following inputs:
        
        {%for (arg, value) in input_binds.items()%}
        - {{ arg }}: {{ value }}
        
        {% endfor %}
        {% else %}
        The function was called without inputs.
        {% endif -%}
        
        What is its output?\
        """)


class AIFunction(BaseModel):
    fn: Optional[Callable] = None
    system: str = system_prompt
    user: str = user_prompt
    name: Optional[str] = None
    description: Optional[str] = None
    instructions: Optional[str] = None
    model: Optional[Any] = None
    functions: Optional[list[Callable]] = Field(default_factory=list)

    @classmethod
    def as_decorator(
        cls,
        fn: Optional[Callable[P, T]] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        system: str = system_prompt,
        user: str = user_prompt,
        instructions: Optional[str] = None,
        functions: Optional[list[Callable]] = None,
        model: str = None,
        **model_kwargs,
    ) -> Callable[P, T]:
        if not fn:
            return functools.partial(
                cls.as_decorator,
                name=name,
                description=description,
                system=system,
                user=user,
                instructions=instructions,
                model=model,
                functions=functions or [],
            )

        model = AIFunction(
            fn=Function(fn),
            name=name,
            description=description,
            system=system,
            user=user,
            instructions=instructions,
            model=ChatCompletion(model=model, **model_kwargs),
            functions=functions or [],
        )

        @functools.wraps(fn)
        async def async_wrapper_function(*args: Any, **kwargs: Any) -> Any:
            return await model.acall(*args, **kwargs)

        @functools.wraps(fn)
        def sync_wrapper_function(*args: Any, **kwargs: Any) -> Any:
            return model.call(*args, **kwargs)

        wrapper_function = (
            async_wrapper_function
            if asyncio.iscoroutinefunction(fn)
            else sync_wrapper_function
        )

        wrapper_function.prompt = model
        wrapper_function.to_chat_completion = model.to_chat_completion
        wrapper_function.create = model.create
        wrapper_function.acreate = model.acreate
        wrapper_function.acall = model.acall
        wrapper_function.map = model.map
        return wrapper_function

    def __call__(self, *args, __schema__=True, **kwargs):
        response = {}
        response["messages"] = self._messages(*args, **kwargs)
        response["functions"] = self._functions(*args, **kwargs)
        response["function_call"] = self._function_call(
            *args, __schema__=__schema__, **kwargs
        )
        if __schema__:
            response["functions"] = response["functions"].schema()
        return response

    def _messages(self, *args, **kwargs):
        return [
            {
                "role": role,
                "content": (
                    Template(getattr(self, role))
                    .render(self.dict(*args, **kwargs))
                    .strip()
                ),
            }
            for role in ["system", "user"]
        ]

    def _functions(self, *args, **kwargs):
        functions = [self.fn.response_model()]
        functions.extend([Function(fn) for fn in self.functions])
        return FunctionRegistry(functions)

    def _function_call(self, *args, __schema__=True, **kwargs):
        if __schema__:
            return {"name": self._functions(*args, **kwargs).schema()[0].get("name")}
        return {"name": self._functions(*args, **kwargs)[0].__name__}

    def to_chat_completion(self, *args, __schema__=False, **kwargs):
        return self.model(**self.__call__(*args, __schema__=__schema__, **kwargs))

    def create(self, *args, **kwargs):
        return self.to_chat_completion(*args, **kwargs).create()

    def call(self, *args, **kwargs):
        completion = self.create(*args, **kwargs)
        return completion.call_function(as_message=False).data

    def map(self, *map_args: list, **map_kwargs: list):
        """
        Map the AI function over a sequence of arguments. Runs concurrently.

        Arguments should be provided as if calling the function normally, but
        each argument must be a list. The function is called once for each item
        in the list, and the results are returned in a list.

        This method can be called synchronously or asynchronously.

        For example, fn.map([1, 2]) is equivalent to [fn(1), fn(2)].

        fn.map([1, 2], x=['a', 'b']) is equivalent to [fn(1, x='a'), fn(2, x='b')].
        """
        if asyncio.get_event_loop().is_running():
            return self.amap(*map_args, **map_kwargs)
        else:
            return asyncio.get_event_loop().run_until_complete(
                self.amap(*map_args, **map_kwargs)
            )

    async def amap(self, *map_args: list, **map_kwargs: list):
        tasks = []
        if map_args:
            max_length = max(len(arg) for arg in map_args)
        else:
            max_length = max(len(v) for v in map_kwargs.values())

        for i in range(max_length):
            call_args = [arg[i] if i < len(arg) else None for arg in map_args]
            call_kwargs = (
                {k: v[i] if i < len(v) else None for k, v in map_kwargs.items()}
                if map_kwargs
                else {}
            )
            tasks.append(self.acall(*call_args, **call_kwargs))

        return await asyncio.gather(*tasks)

    async def acreate(self, *args, **kwargs):
        return await self.to_chat_completion(*args, **kwargs).acreate()

    async def acall(self, *args, **kwargs):
        completion = await self.acreate(*args, **kwargs)
        return completion.call_function(as_message=False).data

    def dict(self, *args, **kwargs):
        return {
            **super().dict(exclude_none=True),
            "functions": self._functions(*args, **kwargs),
            "function_def": self.fn.getsource(),
            "input_binds": self.fn.bind_arguments(*args, **kwargs),
        }


ai_fn = AIFunction.as_decorator
