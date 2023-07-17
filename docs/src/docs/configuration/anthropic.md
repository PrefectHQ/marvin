# Anthropic

Marvin supports Anthropic's Claude 1 and Claude 2 models. In order to use the Anthropic API, you must provide an API key.



## Getting an API key

To obtain an Anthropic API key, follow these steps:

1. [Log in](https://console.anthropic.com/) to your Anthropic account (sign up if you don't have one)
2. Go to the "API Keys" [page](https://console.anthropic.com/account/keys) under your account settings.
3. Click "Create Key." A new API key will be generated. Make sure to copy the key to your clipboard, as you will not be able to see it again.

## Setting the API key

You can set your API key at runtime like this:

```python
import marvin

marvin.settings.anthropic_api_key = YOUR_API_KEY
```

However, it is preferable to pass sensitive settings as an environment variable: `MARVIN_ANTHROPIC_API_KEY`.

To set your Anthropic API key as an environment variable, open your terminal and run the following command, replacing <your API key> with the actual key:

```shell
export MARVIN_ANTHROPIC_API_KEY=<your API key>
```

This will set the key for the duration of your terminal session. To set it more permanently, configure your terminal or its respective env files.

## Using a model

Once your API key is set, you can use any valid Anthropic model by providing it as Marvin's `llm_model` setting:
```python
import marvin

marvin.settings.llm_model = 'claude-2'
```

Marvin will automatically recognize that the `claude-*` family of models use the Anthropic provider. To indicate a provider explicitly, prefix the model name with `anthropic/`. For example: `marvin.settings.llm_model = 'anthropic/claude-2'`.