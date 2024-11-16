# /// script
# dependencies = ["marvin"]
# ///

import marvin
from marvin.client import AsyncMarvinClient
from openai import AsyncClient
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class XAISettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="XAI_")

    api_key: str
    base_url: str = "https://api.x.ai/v1"


class HTTPConcept(BaseModel):
    """A concept in the snippet related to HTTP"""

    name: str
    description: str


def main():
    xai_settings = XAISettings()
    openai_client = AsyncClient(
        api_key=xai_settings.api_key,
        base_url=xai_settings.base_url,
    )

    concepts = marvin.extract(
        data="""
    curl https://api.x.ai/v1/chat/completions \\
      -H "Content-Type: application/json" \\
      -H "Authorization: Bearer $XAI_API_KEY" \\
      -d '{
          "messages": [
            {
              "role": "system",
              "content": "You are Grok, a chatbot inspired by the Hitchhikers Guide to the Galaxy."
            },
            {
              "role": "user",
              "content": "What is the answer to life and universe?"
            }
          ],
          "model": "grok-beta",
          "stream": false,
          "temperature": 0
        }'
    """,
        target=HTTPConcept,
        client=AsyncMarvinClient(client=openai_client),
        model_kwargs={"model": "grok-beta"},
    )

    for concept in concepts:
        print(f"{concept.name}: {concept.description}")


if __name__ == "__main__":
    main()

"""
» uv run hello.py
API Endpoint: The URL used to make the API call, which is 'https://api.x.ai/v1/chat/completions'.
HTTP Method: The HTTP method used for the request, which is 'POST'.
Content-Type Header: The header specifying the content type of the request, which is 'application/json'.
Authorization Header: The header used for authentication, which includes the API key.
Request Body: The JSON payload sent in the request body, containing messages, model, stream, and temperature parameters.
Model: The AI model used for the chat completion, which is 'grok-beta'.
Temperature: The temperature parameter set to 0, indicating no randomness in the response.
"""
