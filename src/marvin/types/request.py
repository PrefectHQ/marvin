import warnings
from typing import Callable, List, Literal, Optional, Type, Union

from pydantic import BaseModel, BaseSettings, Extra, Field, root_validator, validator

from marvin.types import Function


class Request(BaseSettings):
    """
    This is a class for creating Request objects to interact with the GPT-3 API.
    The class contains several configurations and validation functions to ensure
    the correct data is sent to the API.

    """

    messages: Optional[List[dict[str, str]]] = []  # messages to send to the API
    functions: List[Union[dict, Callable]] = None  # functions to be used in the request
    function_call: Optional[Union[dict[Literal["name"], str], Literal["auto"]]] = None

    # Internal Marvin Attributes to be excluded from the data sent to the API
    response_model: Optional[Type[BaseModel]] = Field(default=None)
    evaluate_function_call: bool = Field(default=False)

    class Config:
        exclude = {"response_model"}
        exclude_none = True
        extra = Extra.allow

    @root_validator(pre=True)
    def handle_response_model(cls, values):
        """
        This function validates and handles the response_model attribute.
        If a response_model is provided, it creates a function from the model
        and sets it as the function to call.
        """
        response_model = values.get("response_model")
        if response_model:
            fn = Function.from_model(response_model)
            values["functions"] = [fn]
            values["function_call"] = {"name": fn.__name__}
        return values

    @validator("functions", each_item=True)
    def validate_function(cls, fn):
        """
        This function validates the functions attribute.
        If a Callable is provided, it wraps it with the Function class.
        """
        if isinstance(fn, Callable):
            fn = Function(fn)
        return fn

    def __or__(self, config):
        """
        This method is used to merge two Request objects.
        If the attribute is a list, the lists are concatenated.
        Otherwise, the attribute from the provided config is used.
        """

        touched = config.dict(exclude_unset=True, serialize_functions=False)

        fields = list(
            set(
                [
                    # We exclude none fields from defaults.
                    *self.dict(exclude_none=True, serialize_functions=False).keys(),
                    # We exclude unset fields from the provided config.
                    *config.dict(exclude_unset=True, serialize_functions=False).keys(),
                ]
            )
        )

        for field in fields:
            if isinstance(getattr(self, field, None), list):
                merged = (getattr(self, field, []) or []) + (
                    getattr(config, field, []) or []
                )
                setattr(self, field, merged)
            else:
                setattr(self, field, touched.get(field, getattr(self, field, None)))
        return self

    def merge(self, **kwargs):
        warnings.warn(
            "This is deprecated. Use the | operator instead.", DeprecationWarning
        )
        return self | self.__class__(**kwargs)

    def functions_schema(self, *args, **kwargs):
        """
        This method generates a list of schemas for all functions in the request.
        If a function is callable, its model's schema is returned.
        Otherwise, the function itself is returned.
        """
        return [
            fn.model.schema() if isinstance(fn, Callable) else fn
            for fn in self.functions or []
        ]

    def _dict(self, *args, serialize_functions=True, exclude=None, **kwargs):
        """
        This method returns a dictionary representation of the Request.
        If the functions attribute is present and serialize_functions is True,
        the functions' schemas are also included.
        """
        exclude = exclude or {}
        if serialize_functions:
            exclude["evaluate_function_call"] = True
            exclude["response_model"] = True
        response = super().dict(*args, **kwargs, exclude=exclude)
        if response.get("functions") and serialize_functions:
            response.update({"functions": self.functions_schema()})
        return response

    def dict(self, *args, **kwargs):
        return self._dict(*args, **kwargs)
