from typing import Union, overload
from typing_extensions import Self
from .openai import MarvinClient, AsyncMarvinClient
from openai import Client, AsyncClient


class Marvin:
    @overload
    def __new__(cls: type[Self], client: "Client") -> "MarvinClient":
        ...

    @overload
    def __new__(cls: type[Self], client: "AsyncClient") -> "AsyncMarvinClient":
        ...

    def __new__(
        cls: type[Self], client: Union["Client", "AsyncClient"]
    ) -> Union["MarvinClient", "AsyncMarvinClient"]:
        if isinstance(client, AsyncClient):
            return AsyncMarvinClient(client=client)
        return MarvinClient(client=client)

    @classmethod
    def wrap(
        cls: type[Self], client: Union["Client", "AsyncClient"]
    ) -> Union["Client", "AsyncClient"]:
        if isinstance(client, AsyncClient):
            return AsyncMarvinClient.wrap(client=client)
        return MarvinClient.wrap(client=client)
