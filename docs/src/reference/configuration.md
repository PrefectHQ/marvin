# Settings

Marvin makes use of Pydantic's `BaseSettings` for configuration throughout the package.

## Environment Variables
All settings are configurable via environment variables like `MARVIN_<setting name>`.

For example, in an `.env` file or in your shell config file you might have:
```shell
MARVIN_LOG_LEVEL=DEBUG
MARVIN_LLM_MODEL=gpt-4-0613
MARVIN_LLM_TEMPERATURE=0
```

## Runtime Settings
A runtime settings object is accessible via `marvin.settings` and can be used to access or update settings throughout the package.

For example, to access or change the LLM model used by Marvin on the fly:
```python
In [1]: import marvin

In [2]: marvin.settings.llm_model
Out[2]: 'gpt-4-0613'

In [3]: marvin.settings.llm_model = 'gpt-3.5-turbo-0613'

In [4]: marvin.settings.llm_model
Out[4]: 'gpt-3.5-turbo-0613'
```

## Configuring OpenAI


Marvin uses the OpenAI API to access state-of-the-art language models, including GPT-4 and GPT-3.5. Note that Marvin uses the `gpt-3.5-turbo` model by default. In order to use the OpenAI API, you must provide an API key.

### Getting an API key
To obtain an OpenAI API key, follow these steps:

1. [Log in](https://platform.openai.com/) to your an OpenAI account (sign up if you don't have one)
2. Go to the "API Keys" [page](https://platform.openai.com/account/api-keys) under your account settings.
3. Click "Create new secret key." A new API key will be generated. Make sure to copy the key to your clipboard, as you will not be able to see it again.


### Setting the API key

You can provide your API key as an environment variable (as with any Marvin setting). Marvin will check `MARVIN_OPENAI_API_KEY` followed by `OPENAI_API_KEY`. The latter is more standard and may be accessed by multiple libraries, but the former can be used to scope the API key for Marvin's use only. These docs will use `MARVIN_OPENAI_API_KEY` but either will work.

To set your OpenAI API key as an environment variable, open your terminal and run the following command, replacing <your API key> with the actual key:
```shell
export MARVIN_OPENAI_API_KEY=<your API key>
```

This will set the key for the duration of your terminal session. To set it more permanently, configure your terminal or its respective env files.


