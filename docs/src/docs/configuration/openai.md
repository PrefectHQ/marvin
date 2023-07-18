# OpenAI

Marvin supports OpenAI's GPT-3.5 and GPT-4 models, and uses the `gpt-3.5-turbo` model by default. In order to use the OpenAI API, you must provide an API key.

## Getting an API key

To obtain an OpenAI API key, follow these steps:

1. [Log in](https://platform.openai.com/) to your OpenAI account (sign up if you don't have one)
2. Go to the "API Keys" [page](https://platform.openai.com/account/api-keys) under your account settings.
3. Click "Create new secret key." A new API key will be generated. Make sure to copy the key to your clipboard, as you will not be able to see it again.

## Setting the API key

You can set your API key at runtime like this:

```python
import marvin

marvin.settings.openai_api_key = YOUR_API_KEY
```

However, it is preferable to pass sensitive settings as an environment variable: `MARVIN_OPENAI_API_KEY`. 

To set your OpenAI API key as an environment variable, open your terminal and run the following command, replacing <your API key> with the actual key:

```shell
export MARVIN_OPENAI_API_KEY=<your API key>
```

This will set the key for the duration of your terminal session. To set it more permanently, configure your terminal or its respective env files.

!!! tip "Using OpenAI standard API key locations"
    For convenience, Marvin will respect the `OPENAI_API_KEY` environment variable or a key manually set as `openai.api_key` as long as no Marvin-specific keys were also provided.

## Using a model

Once your API key is set, you can use any valid OpenAI model by providing it as Marvin's `llm_model` setting:
```python
import marvin

marvin.settings.llm_model = 'gpt-4-0613'
```

Marvin will automatically recognize that the `gpt-3.5*` and `gpt-4*` families of models use the OpenAI provider. To indicate a provider explicitly, prefix the model name with `openai/`. For example: `marvin.settings.llm_model = 'openai/gpt-4'`.