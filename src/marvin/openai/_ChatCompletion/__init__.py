# from pydantic import BaseModel, Field, validator, Extra, BaseSettings, root_validator
# from pydantic.main import ModelMetaclass

# from typing import Any, Callable, List, Optional, Type, Union, Literal
# from marvin import settings
# from marvin.types import Function
# from operator import itemgetter
# from marvin.utilities.module_loading import import_string
# import warnings
# import copy
# from marvin.types.request import Request as BaseRequest
# from marvin.engine import ChatCompletionBase


# class Request(BaseRequest):
#     """
#     This is a class for creating Request objects to interact with the GPT-3 API.
#     The class contains several configurations and validation functions to ensure
#     the correct data is sent to the API.

#     """

#     model: str = "gpt-3.5-turbo"  # the model used by the GPT-3 API
#     temperature: float = 0.8  # the temperature parameter used by the GPT-3 API
#     api_key: str = Field(default_factory=settings.openai.api_key.get_secret_value)

#     class Config:
#         exclude = {"response_model"}
#         exclude_none = True
#         extra = Extra.allow

#     def dict(self, *args, serialize_functions=True, exclude=None, **kwargs):
#         """
#         This method returns a dictionary representation of the Request.
#         If the functions attribute is present and serialize_functions is True,
#         the functions' schemas are also included.
#         """

#         # This identity function is here for no reason except to show
#         # readers that custom adapters need only override the dict method.
#         return super().dict(
#             *args, serialize_functions=serialize_functions, exclude=exclude, **kwargs
#         )


# class Response(BaseModel):
#     """
#     This class is used to handle the response from the API.
#     It includes several utility functions and properties to extract useful information
#     from the raw response.
#     """

#     raw: Any  # the raw response from the API
#     request: Any  # the request that generated the response

#     def __init__(self, response, *args, request, **kwargs):
#         super().__init__(raw=response, request=request)

#     def __iter__(self):
#         return self.raw.__iter__()

#     def __next__(self):
#         return self.raw.__next__()

#     def __getattr__(self, name):
#         """
#         This method attempts to get the attribute from the raw response.
#         If it doesn't exist, it falls back to the standard attribute access.
#         """
#         try:
#             return self.raw.__getattr__(name)
#         except AttributeError:
#             return self.__getattribute__(name)

#     @property
#     def message(self):
#         """
#         This property extracts the message from the raw response.
#         If there is only one choice, it returns the message from that choice.
#         Otherwise, it returns a list of messages from all choices.
#         """
#         if len(self.raw.choices) == 1:
#             return next(iter(self.raw.choices)).message
#         return [x.message for x in self.raw.choices]

#     @property
#     def function_call(self):
#         """
#         This property extracts the function call from the message.
#         If the message is a list, it returns a list of function calls from all messages. # noqa
#         Otherwise, it returns the function call from the message.
#         """
#         if isinstance(self.message, list):
#             return [x.function_call for x in self.message]
#         return self.message.function_call

#     @property
#     def callables(self):
#         """
#         This property returns a list of all callable functions from the request.
#         """
#         return [x for x in self.request.functions if isinstance(x, Callable)]

#     @property
#     def callable_registry(self):
#         """
#         This property returns a dictionary mapping function names to functions for all
#         callable functions from the request.
#         """
#         return {fn.__name__: fn for fn in self.callables}

#     def call_function(self, as_message=True):
#         """
#         This method evaluates the function call in the response and returns the result. # noqa
#         If as_message is True, it returns the result as a function message.
#         Otherwise, it returns the result directly.
#         """
#         name, raw_arguments = itemgetter("name", "arguments")(self.function_call)
#         function = self.callable_registry.get(name)
#         arguments = function.model.parse_raw(raw_arguments)
#         value = function(**arguments.dict(exclude_none=True))
#         if as_message:
#             return {"role": "function", "name": name, "content": value}
#         else:
#             return value

#     def to_model(self):
#         """
#         This method parses the function call arguments into the response model and
#         returns the result.
#         """
#         return self.request.response_model.parse_raw(self.function_call.arguments)

#     def __repr__(self, *args, **kwargs):
#         """
#         This method returns a string representation of the raw response.
#         """
#         return self.raw.__repr__(*args, **kwargs)


# class OpenAIChatCompletion(ChatCompletionBase):
#     """
#     This class is used to create and handle chat completions from the API.
#     It provides several utility functions to create the request, send it to the API,
#     and handle the response.
#     """

#     _module: str = "openai.ChatCompletion"  # the module used to interact with the API
#     _request: str = "marvin.openai.ChatCompletion.Request"
#     _response: str = "marvin.openai.ChatCompletion.Response"
#     defaults: Optional[dict] = Field(None, repr=False)  # default configuration values


# ChatCompletion = OpenAIChatCompletion()

# # This is a legacy class that is used to create a ChatCompletion object.
# # It is deprecated and will be removed in a future release.
# ChatCompletionConfig = Request
