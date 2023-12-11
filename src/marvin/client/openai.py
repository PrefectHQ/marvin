from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    NewType,
    Optional,
    TypeVar,
    Union,
    cast,
)

import pydantic
from marvin import settings
from marvin.serializers import create_tool_from_model
from openai import AsyncClient, Client
from openai.types.chat import ChatCompletion
from typing_extensions import Concatenate, ParamSpec

if TYPE_CHECKING:
    from openai._base_client import HttpxBinaryResponseContent
    from openai.types import ImagesResponse


P = ParamSpec("P")
T = TypeVar("T", bound=pydantic.BaseModel)
ResponseModel = NewType("ResponseModel", type[pydantic.BaseModel])
Grammar = NewType("ResponseModel", list[str])


def with_response_model(
    create: Union[Callable[P, "ChatCompletion"], Callable[..., dict[str, Any]]],
    parse_response: bool = False,
) -> Callable[
    Concatenate[
        Optional[Grammar],
        Optional[ResponseModel],
        P,
    ],
    Union["ChatCompletion", dict[str, Any]],
]:
    def create_wrapper(
        grammar: Optional[Grammar] = None,
        response_model: Optional[ResponseModel] = None,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> Any:
        if response_model:
            tool = create_tool_from_model(
                cast(type[pydantic.BaseModel], response_model)
            )
            kwargs.update({"tools": [tool.model_dump()]})
            kwargs.update({"tool_choice": {"type": "function", "function": {"name": tool.function.name}}})  # type: ignore # noqa: E501
        response = create(*args, **kwargs)
        if isinstance(response, ChatCompletion) and parse_response:
            return handle_response_model(
                cast(type[pydantic.BaseModel], response_model), response
            )
        elif isinstance(response, ChatCompletion):
            return response
        else:
            return response

    return create_wrapper


def handle_response_model(response_model: type[T], completion: "ChatCompletion") -> T:
    return [
        response_model.parse_raw(tool_call.function.arguments)  # type: ignore
        for tool_call in completion.choices[0].message.tool_calls  # type: ignore
    ][0]


class MarvinClient(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(
        arbitrary_types_allowed=True,
    )
    client: Client = pydantic.Field(
        default_factory=lambda: Client(
            api_key=getattr(settings.openai.api_key, "get_secret_value", lambda: None)()
        )
    )
    eject: bool = pydantic.Field(
        default=False,
        description=(
            "If local is True, the client will not make any API calls and instead the"
            " raw request will be returned."
        ),
    )

    def chat(
        self,
        grammar: Optional[Grammar] = None,
        response_model: Optional[ResponseModel] = None,
        completion: Optional[Callable[..., "ChatCompletion"]] = None,
        **kwargs: Any,
    ) -> Union["ChatCompletion", dict[str, Any]]:
        if not completion:
            if self.eject:
                completion = lambda **kwargs: kwargs  # type: ignore # noqa: E731
            else:
                completion = self.client.chat.completions.create
        from marvin import settings

        return with_response_model(completion)(  # type: ignore
            grammar,
            response_model,
            **settings.openai.chat.completions.model_dump() | kwargs,
        )

    def paint(
        self,
        **kwargs: Any,
    ) -> "ImagesResponse":
        from marvin import settings

        return self.client.images.generate(
            **settings.openai.images.model_dump() | kwargs
        )

    def speak(
        self,
        **kwargs: Any,
    ) -> "HttpxBinaryResponseContent":
        from marvin import settings

        return self.client.audio.speech.create(
            **settings.openai.audio.speech.model_dump() | kwargs
        )


class MarvinAsyncClient(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(
        arbitrary_types_allowed=True,
    )
    client: Client = pydantic.Field(
        default_factory=lambda: AsyncClient(
            api_key=getattr(settings.openai.api_key, "get_secret_value", lambda: None)()
        )
    )
    eject: bool = pydantic.Field(
        default=False,
        description=(
            "If local is True, the client will not make any API calls and instead the"
            " raw request will be returned."
        ),
    )

    def chat(
        self,
        grammar: Optional[Grammar] = None,
        response_model: Optional[ResponseModel] = None,
        completion: Optional[Callable[..., "ChatCompletion"]] = None,
        **kwargs: Any,
    ) -> Union["ChatCompletion", dict[str, Any]]:
        if not completion:
            if self.eject:
                completion = lambda **kwargs: kwargs  # type: ignore # noqa: E731
            else:
                completion = self.client.chat.completions.create
        from marvin import settings

        return with_response_model(completion)(  # type: ignore
            grammar,
            response_model,
            **settings.openai.chat.completions.model_dump() | kwargs,
        )

    def paint(
        self,
        **kwargs: Any,
    ) -> "ImagesResponse":
        from marvin import settings

        return self.client.images.generate(
            **settings.openai.images.model_dump() | kwargs
        )

    def speak(
        self,
        **kwargs: Any,
    ) -> "HttpxBinaryResponseContent":
        from marvin import settings

        return self.client.audio.speech.create(
            **settings.openai.audio.speech.model_dump() | kwargs
        )
