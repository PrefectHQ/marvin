import marvin

from .openai import OpenAIChatLLM

CONTEXT_SIZES = {
    "gpt-3.5-turbo-16k-0613": 16384,
    "gpt-3.5-turbo-16k": 16384,
    "gpt-3.5-turbo-0613": 4096,
    "gpt-3.5-turbo": 4096,
    "gpt-3.5-turbo-1106": 16384,
    "gpt-4-32k-0613": 32768,
    "gpt-4-32k": 32768,
    "gpt-4-0613": 8192,
    "gpt-4": 8192,
    "gpt-4-1106": 128000,
    "gpt-4-turbo": 128000,
    "analytics-gpt35-1106": 16384,
    "analytics-gpt4-turbo": 128000
}

class AzureOpenAIChatLLM(OpenAIChatLLM):
    model: str = "gpt-35-turbo-0613"

    @property
    def context_size(self) -> int:
        if self.model in CONTEXT_SIZES:
            return CONTEXT_SIZES[self.model]
        else:
            for model_prefix, context in CONTEXT_SIZES:
                if self.model.startswith(model_prefix):
                    return context
        return 8192

    def _get_openai_settings(self) -> dict:
        # do not load the base openai settings; any azure settings must be set
        # explicitly
        openai_kwargs = {}

        if marvin.settings.azure_openai.api_key:
            openai_kwargs["api_key"] = (
                marvin.settings.azure_openai.api_key.get_secret_value()
            )
        else:
            raise ValueError(
                "Azure OpenAI API key not set. Please set it or use the"
                " MARVIN_AZURE_OPENAI_API_KEY environment variable."
            )
        if marvin.settings.azure_openai.api_base:
            openai_kwargs["api_base"] = marvin.settings.azure_openai.api_base
        if marvin.settings.azure_openai.api_version:
            openai_kwargs["api_version"] = marvin.settings.azure_openai.api_version
        return openai_kwargs
