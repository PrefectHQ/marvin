from typing import List

import httpx
from pydantic import HttpUrl

from marvin.loaders.base import Loader
from marvin.models.documents import Document


class OpenAPISpecLoader(Loader):
    """A loader that loads documents from a OpenAPI spec.

    Example:
        Store the OpenAPI spec for the Prefect Cloud API as documents
        ```python
            import asyncio
            loader = OpenAPISpecLoader(openapi_spec_url='https://api.prefect.cloud/api/openapi.json')
            asyncio.run(loader.load_and_store())
        ```
    """

    openapi_spec_url: HttpUrl

    @property
    def api_doc_url(self) -> str:
        return self.openapi_spec_url.replace("/openapi.json", "/docs").replace(
            "api.", "app."
        )

    async def load(self) -> List[Document]:
        response = httpx.get(self.openapi_spec_url)
        response.raise_for_status()

        api_doc = response.json()
        paths = api_doc.get("paths", {})
        documents = []

        for path, methods in paths.items():
            for method, details in methods.items():
                if not details.get("tags"):
                    continue
                parameters = details.get("parameters", [])

                path_params = [param for param in parameters if param["in"] == "path"]
                query_params = [param for param in parameters if param["in"] == "query"]

                documents.extend(
                    await Document(
                        text=details.get("description", ""),
                        metadata={
                            "title": f"{method.upper()} {path}",
                            "link": f'{self.api_doc_url}#tag/{details.get("tags")[0]}/operation/{details.get("operationId")}',  # noqa: E501
                            "path": path,
                            "method": method,
                            "operationId": details.get("operationId"),
                            "path_params": str(path_params),
                            "query_params": str(query_params),
                        },
                    ).to_excerpts()
                )

        return documents
