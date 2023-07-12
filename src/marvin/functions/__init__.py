import functools
import inspect
import re
from typing import Callable, TypeVar, Optional, Any, Type

from fastapi.routing import APIRouter

from marvin.utilities.types import function_to_model


T = TypeVar("T")
A = TypeVar("A")


class Function:
    def __init__(
        self, *, fn: Callable[[A], T] = None, name: str = None, description: str = None
    ) -> None:
        self.fn = fn
        self.name = name or self.fn.__name__
        self.description = description or self.fn.__doc__

        super().__init__()

    @property
    def model(self):
        return function_to_model(self.fn, name=self.name, description=self.description)

    @property
    def signature(self):
        return inspect.signature(self.fn)

    @property
    def source_code(self):
        source_code = inspect.cleandoc(inspect.getsource(self.fn))
        if match := re.search(re.compile(r"(\bdef\b.*)", re.DOTALL), source_code):
            source_code = match.group(0)
        return source_code

    @property
    def return_annotation(self):
        return_annotation = self.signature.return_annotation
        if return_annotation is inspect._empty:
            return return_annotation, False
        return return_annotation

    def arguments(self, *args, **kwargs):
        bound_args = self.signature.bind(*args, **kwargs)
        bound_args.apply_defaults()
        return bound_args.arguments

    def schema(self, *args, name: str = None, description: str = None, **kwargs):
        schema = self.model.schema(*args, **kwargs)
        return {
            "name": name or schema.pop("title"),
            "description": description or self.fn.__doc__,
            "parameters": schema,
        }


def FunctionDecoratorFactory(
    name: str = "marvin",
    func_class: Type[T] = None,
    in_place=True,
) -> Callable[[A], T]:
    def decorator(fn: Callable[[A], T] = None) -> Callable[[A], T]:
        if fn is None:
            return functools.partial(decorator)
        elif in_place:
            fn = func_class(fn=fn)
        else:
            instance = func_class(fn=fn)
            setattr(fn, name, instance)
            for method in dir(instance):
                is_method_private = method.startswith("__")
                if not is_method_private:
                    setattr(fn, method, getattr(instance, method))
        return fn

    return decorator


marvin_fn = FunctionDecoratorFactory(name="openai", func_class=Function)


class FunctionRegistry(APIRouter):
    def __init__(self, function_decorator=marvin_fn, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.function_decorator = function_decorator

    @property
    def endpoints(self):
        # Returns literal functions.
        return [route.endpoint for route in self.routes]

    @property
    def schema(self):
        # Returns JSON Schema of functions.
        return [self.function_decorator(fn=fn).schema() for fn in self.endpoints]

    @property
    def functions(self):
        # Returns function classes.
        return [self.function_decorator(fn=fn) for fn in self.endpoints]

    def include(self, registry: "FunctionRegistry", *args, **kwargs):
        super().include_router(registry, *args, **kwargs)
        # Add some 50-IQ idempotency.
        self.routes = list({x.name: x for x in self.routes}.values())

    def register(self, fn: Optional[Callable] = None, **kwargs: Any) -> Callable:
        def decorator(fn: Callable, *args) -> Callable:
            fn_class = self.function_decorator(fn=fn, **kwargs)
            self.add_api_route(
                **{
                    **{
                        "name": fn_class.name,
                        "path": f"/{fn_class.name}",
                        "endpoint": fn,
                        "description": fn_class.description,
                        "methods": ["POST"],
                    },
                    **kwargs,
                }
            )
            return fn

        if fn:
            # if the decorator was called with parentheses
            return decorator(fn)
        else:
            # else, return the decorator to be called later
            return decorator
