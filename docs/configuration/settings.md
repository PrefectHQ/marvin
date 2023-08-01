# Settings

Marvin makes use of Pydantic's `BaseSettings` for configuration throughout the package.

## Environment Variables
All settings are configurable via environment variables like `MARVIN_<setting name>`.

For example, in an `.env` file or in your shell config file you might have:
```shell
MARVIN_LOG_LEVEL=DEBUG
MARVIN_LLM_MODEL=openai/gpt-4
MARVIN_LLM_TEMPERATURE=0
```

## Runtime Settings
A runtime settings object is accessible via `marvin.settings` and can be used to access or update settings throughout the package.

For example, to access or change the LLM model used by Marvin at runtime:
```python
import marvin

marvin.settings.llm_model
# 'openai/gpt-4'

marvin.settings.llm_model = 'openai/gpt-3.5-turbo'

marvin.settings.llm_model
# 'openai/gpt-3.5-turbo'
```

## LLM Providers

Marvin supports multiple LLM providers, including [OpenAI](../providers#openai) and [Anthropic](../providers#anthropic). After configuring your credentials appropriately, you can use any supported model by setting `marvin.settings.llm_model` appropriately. 

Valid `llm_model` settings are strings with the form `"{provider_key}/{model_name}"`. For example, `"openai/gpt-3.5-turbo"`, `anthropic/claude-2`, or `azure_openai/gpt-4`.


| Provider | Provider Key | Models | Notes |
| --- | --- | --- | --- |
| OpenAI | `openai` | `gpt-3.5-turbo`, `gpt-4` (default), or any other [compatible model](https://platform.openai.com/docs/models/) | Marvin is generally tested and optimized with this provider. |
| Anthropic | `anthropic` | `claude-2`, `claude-instant-1` or any other [compatible model](https://docs.anthropic.com/claude/reference/selecting-a-model) | Available in Marvin 1.1|
| Azure OpenAI Service | `azure_openai` | `gpt-35-turbo`, `gpt-4`, or any other [compatible model](https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/models) | The Azure OpenAI Service shares all the same configuration options as the OpenAI models, as well as a few additional ones. Available in Marvin 1.1.  | 

## LLM Configuration

To configure LLM models globally, you can adjust the following settings. Note that these become the default settings for all models, but you can always set these on a per-model or per-component basis.

| Setting | Env Variable | Runtime Variable | Default | Notes |
| --- | --- | --- |  :---: | --- |
| LLM model | `MARVIN_LLM_MODEL` | `marvin.settings.llm_model` | `openai/gpt-3.5-turbo` | Set the model as `{provider}/{model}`. Defaults to OpenAI's GPT-3.5 model. |
| Temperature | `MARVIN_LLM_TEMPERATURE` | `marvin.settings.llm_temperature` | 0.8 | |
| Max tokens | `MARVIN_LLM_MAX_TOKENS` | `marvin.settings.llm_max_tokens` | 1500 | The maximum number of tokens in a model completion |
| Timeout | `MARVIN_LLM_REQUEST_TIMEOUT_SECONDS` | `marvin.settings.llm_request_timeout_seconds` | 600.0 ||