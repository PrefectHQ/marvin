"""
The engine module is the interface to external LLM providers.
"""
from pydantic import BaseModel, BaseSettings, Extra, Field, root_validator, validator
from typing import Any, Callable, List, Optional, Type, Union, Literal
from marvin import settings
from marvin.types import Function
from operator import itemgetter
from marvin.utilities.module_loading import import_string
import warnings
import copy


class ChatCompletionBase(BaseModel):
    """
    This class is used to create and handle chat completions from the API.
    It provides several utility functions to create the request, send it to the API,
    and handle the response.
    """

    _module: str = "openai.ChatCompletion"  # the module used to interact with the API
    _request: str = "marvin.openai.ChatCompletion.Request"
    _response: str = "marvin.openai.ChatCompletion.Response"
    _create: str = "create"  # the name of the create method in the API model
    _acreate: str = (  # the name of the asynchronous create method in the API model
        "acreate"
    )
    defaults: Optional[dict] = Field(None, repr=False)  # default configuration values

    def __init__(self, module_path: str = None, config_path: str = None, **kwargs):
        super().__init__(_module=module_path, _config=config_path, defaults=kwargs)

    @property
    def module(self):
        """
        This property imports and returns the API model.
        """
        return import_string(self._module)

    @property
    def model(self):
        """
        This property imports and returns the API model.
        """
        return self.module

    def request(self, *args, **kwargs):
        """
        This method imports and returns a configuration object.
        """
        return import_string(self._request)(*args, **(kwargs or self.defaults or {}))

    @property
    def response_class(self, *args, **kwargs):
        """
        This method imports and returns a configuration object.
        """
        return import_string(self._response)

    def prepare_request(self, *args, **kwargs):
        """
        This method prepares a request and returns it.
        """
        request = self.request() | self.request(**kwargs)
        payload = request.dict(exclude_none=True, exclude_unset=True)
        return request, payload

    def create(self=None, *args, **kwargs):
        """
        This method creates a request and sends it to the API.
        It returns a Response object with the raw response and the request.
        """
        request, request_dict = self.prepare_request(*args, **kwargs)
        create = getattr(self.model, self._create)
        response = self.response_class(create(**request_dict), request=request)
        if request.evaluate_function_call and response.function_call:
            return response.call_function(as_message=True)
        return response

    async def acreate(self, *args, **kwargs):
        """
        This method is an asynchronous version of the create method.
        It creates a request and sends it to the API asynchronously.
        It returns a Response object with the raw response and the request.
        """
        request, request_dict = self.prepare_request(*args, **kwargs)
        acreate = getattr(self.model, self._acreate)
        response = self.response_class(await acreate(**request_dict), request=request)
        if request.evaluate_function_call and response.function_call:
            return await response.acall_function(as_message=True)
        return response

    def __call__(self, *args, **kwargs):
        self = copy.deepcopy(self)
        request = self.request()
        passed = self.__class__(**kwargs).request()
        self.defaults = (request | passed).dict(serialize_functions=False)
        return self
