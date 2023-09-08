from typing import Literal

from pydantic import Field, SecretStr

from ..._compat import V1Field
from .base import MarvinBaseSettings


class AzureOpenAIBaseSettings(MarvinBaseSettings):
    api_type: Literal["azure", "azure_ad"] = "azure"

    api_base: str | None = Field(
        default=None,
        description=(
            "The endpoint of the Azure OpenAI API. This should have the form"
            " https://YOUR_RESOURCE_NAME.openai.azure.com"
        ),
    )
    api_version: str | None = Field(
        default="2023-07-01-preview", description="The API version"
    )

    api_key: SecretStr | None = V1Field(
        default=None,
        env=[
            "MARVIN_AZURE_API_KEY",
            "MARVIN_OPENAI_API_KEY",
            "OPENAI_API_KEY",
            "AZURE_API_KEY",
        ],
    )

    deployment_name: str | None = Field(
        default=None,
        description=(
            "This will correspond to the custom name you chose for your deployment when"
            " you deployed a model."
        ),
    )

    class Config(MarvinBaseSettings.Config):
        env_prefix = "MARVIN_AZURE_OPENAI_"
