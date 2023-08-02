from marvin.pydantic import Field, SecretStr
from marvin.utilities.module_loading import import_string
from marvin import settings
from typing import Literal
from marvin.core.ChatCompletion.base import (
    BaseChatCompletion,
    BaseChatCompletionSettings,
    BaseChatRequest,
    BaseChatResponse,
)


class ChatCompletionSettings(BaseChatCompletionSettings):
    """
    Provider-specific settings.
    """

    api_key: SecretStr = Field(env=["MARVIN_AZURE_API_KEY"])
    api_type: Literal["azure", "azure_ad"] = "azure"
    api_base: str = Field(
        None,
        description=(
            "The endpoint of the Azure OpenAI API. This should have the form"
            " https://YOUR_RESOURCE_NAME.openai.azure.com"
        ),
    )
    api_version: str = Field("2023-07-01-preview", description="The API version")
    deployment_name: str = Field(
        None,
        description=(
            "This will correspond to the custom name you chose for your deployment when"
            " you deployed a model."
        ),
    )

    class Config(BaseChatCompletionSettings.Config):
        env_prefix = "MARVIN_AZURE_OPENAI_"
        exclude_none = True


class ChatRequest(BaseChatRequest):
    _config = ChatCompletionSettings()


class ChatResponse(BaseChatResponse):
    @property
    def message(self):
        """
        This property extracts the message from the raw response.
        If there is only one choice, it returns the message from that choice.
        Otherwise, it returns a list of messages from all choices.
        """
        if len(self.raw.choices) == 1:
            return next(iter(self.raw.choices)).message
        return [x.message for x in self.raw.choices]

    def function_call(self, *args, **kwargs):
        """
        This property extracts the function call from the message.
        If the message is a list, it returns a list of function calls from all messages.
        Otherwise, it returns the function call from the message.
        """
        if isinstance(self.message, list):
            return [x.function_call for x in self.message]
        return getattr(self.message, "function_call", None)


class ChatCompletion(BaseChatCompletion):
    _module: str = "openai.ChatCompletion"
    _create: str = "create"
    _acreate: str = "acreate"

    _request_class: ChatRequest = ChatRequest
    _response_class: ChatResponse = ChatResponse

    def prepare_request(self, **kwargs):
        """
        Nothing to change since BaseChatCompletion is designed
        off of the OpenAI API.
        """
        return super().prepare_request(**kwargs)
