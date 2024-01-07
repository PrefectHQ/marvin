import inspect
import textwrap
from typing import Any, Callable, List, Optional

from pydantic import BaseModel, Field, computed_field

from marvin.utilities.asyncio import run_sync


class ParameterModel(BaseModel):
    name: str
    annotation: Optional[str]
    default: Optional[str]


class PythonFunction(BaseModel, arbitrary_types_allowed=True):
    function: Callable = Field(description="Original function object")
    signature: inspect.Signature = Field(description="Function signature object")
    name: str = Field(description="Name of the function")
    docstring: Optional[str] = Field(None, description="Docstring of the function")
    parameters: List[ParameterModel] = Field(description="Parameters of the function")
    return_annotation: Optional[Any] = Field(
        None, description="Return annotation of the function."
    )
    source_code: str = Field(description="Source code of the function")
    bound_parameters: dict[str, Any] = Field(
        {}, description="Parameters bound with values"
    )
    return_value: Optional[Any] = Field(
        None, description="Return value of the function call"
    )

    @computed_field
    @property
    def definition(self) -> str:
        docstring = inspect.cleandoc(self.docstring) if self.docstring else ""
        formatted_docstring = textwrap.indent(
            f'"""\n{docstring}\n"""' if docstring else "",
            prefix="    ",
        )
        return f"def {self.name}{self.signature}:\n{formatted_docstring}".strip()

    @classmethod
    def from_function(cls, func: Callable, **kwargs) -> "PythonFunction":
        name = kwargs.pop("name", func.__name__)
        docstring = kwargs.pop("docstring", func.__doc__)
        sig = inspect.signature(func)
        parameters = [
            ParameterModel(
                name=name,
                annotation=(
                    str(param.annotation)
                    if param.annotation is not param.empty
                    else None
                ),
                default=(
                    repr(param.default) if param.default is not param.empty else None
                ),
            )
            for name, param in sig.parameters.items()
        ]
        source_code = inspect.getsource(func).strip()

        function_dict = {
            "function": func,
            "signature": sig,
            "name": name,
            "docstring": inspect.cleandoc(docstring) if docstring else None,
            "parameters": parameters,
            "return_annotation": sig.return_annotation,
            "source_code": source_code,
        }

        function_dict.update(kwargs)

        return cls(**function_dict)

    @classmethod
    def from_function_call(cls, func: Callable, *args, **kwargs) -> "PythonFunction":
        sig = inspect.signature(func)

        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()

        return_value = func(*bound.args, **bound.kwargs)
        if inspect.iscoroutine(return_value):
            return_value = run_sync(return_value)

        instance = cls.from_function(
            func,
            bound_parameters={k: v for k, v in bound.arguments.items()},
            return_value=return_value,
        )

        return instance
