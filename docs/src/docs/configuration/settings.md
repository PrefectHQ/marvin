# Settings

Marvin makes use of Pydantic's `BaseSettings` for configuration throughout the package.

## Environment Variables
All settings are configurable via environment variables like `MARVIN_<setting name>`.

For example, in an `.env` file or in your shell config file you might have:
```shell
MARVIN_LOG_LEVEL=DEBUG
MARVIN_LLM_MODEL=gpt-4
MARVIN_LLM_TEMPERATURE=0
```

## Runtime Settings
A runtime settings object is accessible via `marvin.settings` and can be used to access or update settings throughout the package.

For example, to access or change the LLM model used by Marvin at runtime:
```python
import marvin

marvin.settings.llm_model
# 'gpt-4'

marvin.settings.llm_model = 'gpt-3.5-turbo'

marvin.settings.llm_model
# 'gpt-3.5-turbo'
```

## LLM Providers

Marvin supports multiple LLM providers, including [OpenAI](/src/docs/configuration/openai) and [Anthropic]((/src/docs/configuration/anthropic)). After configuring your credentials appropriately, you can use any supported model by setting `marvin.settings.llm_model` appropriately. 

Valid `llm_model` settings are strings with the form `"{provider_key}/{model_name}"`. For example, `"openai/gpt-3.5-turbo"`. 

For well-known models, you may provide the model name without a provider key. These models include:

- the `gpt-3.5-*` family from OpenAI
- the `gpt-4*` family from OpenAI
- the `claude-*` family from Anthropic



| Provider | Provider Key | Models | Notes |
| --- | --- | --- | --- |
| OpenAI | `openai` | `gpt-3.5-turbo` (default), `gpt-4`, or any other [compatible model](https://platform.openai.com/docs/models/) | Marvin is generally tested and optimized with this provider. |
| Anthropic | `anthropic` | `claude-2`, `claude-instant-1` or any other [compatible model](https://docs.anthropic.com/claude/reference/selecting-a-model) | |