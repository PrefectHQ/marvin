from pydantic import BaseModel


class DefaultSettings(BaseModel):
    default_model_path: str = "marvin.llms.providers.default"
    default_model_name: str = "gpt-3.5-turbo"
    default_model_api_key_name: str = "OPENAI_API_KEY"


default_settings = DefaultSettings().dict()
