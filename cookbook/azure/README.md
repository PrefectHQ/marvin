# Azure OpenAI with Marvin
It is possible to use Azure OpenAI with `marvin` via the `AzureOpenAI` client offered in `openai` 1.x.

!!! Note
    Azure OpenAI often lags behind the latest version of OpenAI in terms of functionality, therefore some features may not work with Azure OpenAI. If you encounter problems, please check that the underlying functionality is supported by Azure OpenAI before reporting an issue.

## Settings
After setting up your Azure OpenAI account and deployment, it is recommended you save these settings in your `~/.marvin/.env` file.

```bash
» cat ~/.marvin/.env | rg AZURE
MARVIN_USE_AZURE_OPENAI=true # must be set to use Azure OpenAI
MARVIN_AZURE_OPENAI_API_KEY=<your-api-key>
MARVIN_AZURE_OPENAI_ENDPOINT=https://<your-endpoint>.openai.azure.com/
MARVIN_AZURE_OPENAI_API_VERSION=2023-12-01-preview # or whatever is the latest
MARVIN_AZURE_OPENAI_DEPLOYMENT_NAME=gpt-35-turbo-0613 # or whatever you named your deployment
```