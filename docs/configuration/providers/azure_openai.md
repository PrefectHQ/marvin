# Azure OpenAI Service

!!! abstract "Available in Marvin 1.1"

Marvin supports Azure's OpenAI service. In order to use the Azure service, you must provide an API key.


## Configuration

To use the Azure OpenAI service, you can set the following configuration options:

| Setting | Env Variable | Runtime Variable | Required? | Notes |
| --- | --- | --- |  :---: | --- |
| API key | `MARVIN_AZURE_OPENAI_API_KEY` | `marvin.settings.azure_openai.api_key` | ✅ | |
| API base | `MARVIN_AZURE_OPENAI_API_BASE` | `marvin.settings.azure_openai.api_base` | ✅ | The API endpoint; this should have the form `https://YOUR_RESOURCE_NAME.openai.azure.com` |
| Deployment name | `MARVIN_AZURE_OPENAI_DEPLOYMENT_NAME` | `marvin.settings.azure_openai.deployment_name` | ✅ | |
| API type | `MARVIN_AZURE_OPENAI_API_TYPE` | `marvin.settings.azure_openai.api_type` |  | Either `azure` (the default) or `azure_ad` (to use Microsoft Active Directory to authenticate to your Azure endpoint).|

## Using a model

Once the provider is configured, you can use any Azure OpenAI model by providing it as Marvin's `llm_model` setting:
```python
import marvin

marvin.settings.llm_model = 'azure_openai/gpt-35-turbo'
```