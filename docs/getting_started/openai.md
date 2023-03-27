# Configuring OpenAI

Marvin uses the OpenAI API to access state-of-the-art language models, including the GPT-3.5 ("ChatGPT") and GPT-4 models. These models are capable of generating natural language text that is often indistinguishable from human-written text. By integrating with the OpenAI API, Marvin provides a simple interface for accessing these powerful language models and incorporating them into your own applications.

To use Marvin, you need to obtain an OpenAI API key and set it as an environment variable. This API key is used to authenticate your requests to the OpenAI API. This is the only *required* configuration for using Marvin.


## Getting an API key
To obtain an OpenAI API key, follow these steps:

1. [Log in](https://platform.openai.com/) to your an OpenAI account (sign up if you don't have one)
2. Go to the "API Keys" [page](https://platform.openai.com/account/api-keys) under your account settings.
3. Click "Create new secret key." A new API key will be generated. Make sure to copy the key to your clipboard, as you will not be able to see it again.

## Configuring your API key

### Marvin CLI

The easiest way to set your API key is by running `marvin setup-openai`, which will let you store your API key in your Marvin configuration file. 

### Environment variables
Alternatively, you can provide your API key as an environment variable (as with any Marvin setting). Marvin will check `MARVIN_OPENAI_API_KEY` followed by `OPENAI_API_KEY`. The latter is more standard and may be accessed by multiple libraries, but the former can be used to scope the API key for Marvin's use only. These docs will use `MARVIN_OPENAI_API_KEY` but either will work.

To set your OpenAI API key as an environment variable, open your terminal and run the following command, replacing <your API key> with the actual key:
```shell
export MARVIN_OPENAI_API_KEY=<your API key>
```

This will set the key for the duration of your terminal session. To set it more permanently, configure your terminal or its respective env files.
