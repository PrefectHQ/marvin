## OpenAI

Marvin supports OpenAI's GPT-3.5 and GPT-4 models, and uses the `openai/gpt-4` model by default. In order to use the OpenAI API, you must provide an API key.

### Configuration

To use OpenAI models, you can set the following configuration options:

| Setting | Env Variable | Runtime Variable | Required? | Notes |
| --- | --- | --- |  :---: | --- |
| API key | `MARVIN_OPENAI_API_KEY` | `marvin.settings.openai.api_key` | ✅ | |

!!! tip "Using the Azure OpenAI Service"
    To use the Azure OpenAI Service, configure it [explicitly](#azure-openai-service).
### Getting an API key

To obtain an OpenAI API key, follow these steps:

1. [Log in](https://platform.openai.com/) to your OpenAI account (sign up if you don't have one)
2. Go to the "API Keys" [page](https://platform.openai.com/account/api-keys) under your account settings.
3. Click "Create new secret key." A new API key will be generated. Make sure to copy the key to your clipboard, as you will not be able to see it again.

### Setting the API key

You can set your API key at runtime like this:

```python
import marvin

# Marvin 1.1+
marvin.settings.openai.api_key = YOUR_API_KEY

# Marvin 1.0
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

### Using a model

Once your API key is set, you can use any valid OpenAI model by providing it as Marvin's `llm_model` setting:
```python
import marvin

marvin.settings.llm_model = 'openai/gpt-4-0613'
```

## Anthropic

!!! abstract "Available in Marvin 1.1"

Marvin supports Anthropic's Claude 1 and Claude 2 models. In order to use the Anthropic API, you must provide an API key.

!!! tip "Installing the Anthropic provider"
    To use the Anthropic provider, you must have the `anthropic` Python client installed. You can do this by installing Marvin as `pip install "marvin[anthropic]"`


!!! warning "Anthropic is not optimized for calling functions"
    Anthropic's models are not fine-tuned for calling functions or generating structured outputs. Therefore, Marvin adds a significant number of additional instructions to get Anthropic models to mimic this behavior. Empirically, this works very well for most Marvin components, including functions, models, and classifiers. However, it may not perform as well for more complex AI Applications.

### Configuration

To use Anthropic models, you can set the following configuration options:

| Setting | Env Variable | Runtime Variable | Required? | Notes |
| --- | --- | --- |  :---: | --- |
| API key | `MARVIN_ANTHROPIC_API_KEY` | `marvin.settings.anthropic.api_key` | ✅ | |

### Getting an API key

To obtain an Anthropic API key, follow these steps:

1. [Log in](https://console.anthropic.com/) to your Anthropic account (sign up if you don't have one)
2. Go to the "API Keys" [page](https://console.anthropic.com/account/keys) under your account settings.
3. Click "Create Key." A new API key will be generated. Make sure to copy the key to your clipboard, as you will not be able to see it again.

### Setting the API key

You can set your API key at runtime like this:

```python
import marvin

marvin.settings.anthropic.api_key = YOUR_API_KEY
```

However, it is preferable to pass sensitive settings as an environment variable: `MARVIN_ANTHROPIC_API_KEY`.

To set your Anthropic API key as an environment variable, open your terminal and run the following command, replacing <your API key> with the actual key:

```shell
export MARVIN_ANTHROPIC_API_KEY=<your API key>
```

This will set the key for the duration of your terminal session. To set it more permanently, configure your terminal or its respective env files.

### Using a model

Once your API key is set, you can use any valid Anthropic model by providing it as Marvin's `llm_model` setting:
```python
import marvin

marvin.settings.llm_model = 'claude-2'
```

Marvin will automatically recognize that the `claude-*` family of models use the Anthropic provider. To indicate a provider explicitly, prefix the model name with `anthropic/`. For example: `marvin.settings.llm_model = 'anthropic/claude-2'`.

## Azure OpenAI Service

!!! abstract "Available in Marvin 1.1"

Marvin supports Azure's OpenAI service. In order to use the Azure service, you must provide an API key.


### Configuration

To use the Azure OpenAI service, you can set the following configuration options:

| Setting | Env Variable | Runtime Variable | Required? | Notes |
| --- | --- | --- |  :---: | --- |
| API key | `MARVIN_AZURE_OPENAI_API_KEY` | `marvin.settings.azure_openai.api_key` | ✅ | |
| API base | `MARVIN_AZURE_OPENAI_API_BASE` | `marvin.settings.azure_openai.api_base` | ✅ | The API endpoint; this should have the form `https://YOUR_RESOURCE_NAME.openai.azure.com` |
| Deployment name | `MARVIN_AZURE_OPENAI_DEPLOYMENT_NAME` | `marvin.settings.azure_openai.deployment_name` | ✅ | |
| API type | `MARVIN_AZURE_OPENAI_API_TYPE` | `marvin.settings.azure_openai.api_type` |  | Either `azure` (the default) or `azure_ad` (to use Microsoft Active Directory to authenticate to your Azure endpoint).|

### Using a model

Once the provider is configured, you can use any Azure OpenAI model by providing it as Marvin's `llm_model` setting:
```python
import marvin

marvin.settings.llm_model = 'azure_openai/gpt-35-turbo'
```