# Configuration

## LLMs

### Selecting an LLM backend

Marvin supports various LLM backends. The default is OpenAI's GPT-3.5 model, but you can choose from a number of different providers, including OpenAI, Anthropic, Azure, HuggingFaceHub, and more. To change the LLM model, set the `MARVIN_LLM_BACKEND` and `MARVIN_LLM_MODEL` variables appropriately. For some common models, the backend can be selected automatically (e.g. any GPT model, any Claude model).

At this time, valid options include:

| Backend | Description | Models | Notes |
| --- | --- | --- | --- |
| `OpenAIChat` (default) | OpenAI's chat models | `gpt-3.5-turbo` (default), `gpt-4` | Marvin is generally tested and optimized with this backend. |
| `AzureOpenAIChat` | OpenAI chat models via Azure | (same as `OpenAIChat`) |
| `OpenAI` | OpenAI's completion models | `text-davinci-003`, etc. |
| `AzureOpenAI` | OpenAI completion models via Azure | (same as `OpenAI`) |
| `Anthropic` | Anthropic models | `claude-v1`, `claude-v1.3`, `claude-v1.3-100k`, any other [available model](https://console.anthropic.com/docs/api/reference#parameters) |
| `HuggingFaceHub` | Models hosted on HuggingFaceHub | Any valid `repo/model` combination | Support for these models is **experimental** and quality will vary. |

 
Models may have unique settings which are detailed below.

### OpenAI

Marvin can use the OpenAI API to access state-of-the-art language models, including GPT-4 and GPT-3.5. These models are capable of generating natural language text that is often indistinguishable from human-written text. By integrating with the OpenAI API, Marvin provides a simple interface for accessing these powerful language models and incorporating them into your own applications.

Note that Marvin uses OpenAI's gpt-3.5-turbo model by default, but you must provide an API key for this to work.

#### Getting an API key
To obtain an OpenAI API key, follow these steps:

1. [Log in](https://platform.openai.com/) to your an OpenAI account (sign up if you don't have one)
2. Go to the "API Keys" [page](https://platform.openai.com/account/api-keys) under your account settings.
3. Click "Create new secret key." A new API key will be generated. Make sure to copy the key to your clipboard, as you will not be able to see it again.

#### Setting the API key via CLI

The easiest way to set your API key is by running `marvin setup-openai`, which will let you store your API key in your Marvin configuration file. 

#### Environment variables
Alternatively, you can provide your API key as an environment variable (as with any Marvin setting). Marvin will check `MARVIN_OPENAI_API_KEY` followed by `OPENAI_API_KEY`. The latter is more standard and may be accessed by multiple libraries, but the former can be used to scope the API key for Marvin's use only. These docs will use `MARVIN_OPENAI_API_KEY` but either will work.

To set your OpenAI API key as an environment variable, open your terminal and run the following command, replacing <your API key> with the actual key:
```shell
export MARVIN_OPENAI_API_KEY=<your API key>
```

This will set the key for the duration of your terminal session. To set it more permanently, configure your terminal or its respective env files.

## Database
Running Marvin as an API server requires a database. By default, Marvin uses a SQLite database stored at `~/.marvin/marvin.sqlite`. You can set the database location and type by changing the `MARVIN_DATABASE_CONNECTION_URL` setting. Marvin is tested with SQLite and Postgres. It may also work with other database supported by SQLAlchemy, so long as there are async drivers available.

!!! warning
    Marvin's server is under active development, so you should treat its database as ephemeral and able to be destroyed at any time. At this time, Marvin does not include database migrations, which means that upgrading your database schema requires destroying it. This is a high-priority area for improvement.


## Settings
Marvin has many configurable settings that can be loaded from `marvin.settings`.


### Setting values
All settings can be configured via environment variable using the pattern `MARVIN_<name of setting>`. For example, to set the log level, set `MARVIN_LOG_LEVEL=DEBUG` and verify that `marvin.settings.log_level == 'DEBUG'`. Settings can also be set at runtime through assignment (e.g. `marvin.settings.log_level = 'DEBUG'`) but this is not recommended because some code might haved loaded configuration on import and consequently never pick up the updated value.

### Important settings

#### Global
**Log level**: Set the log level
```
MARVIN_LOG_LEVEL=INFO
```
**Verbose mode**: Logs extra information, especially when the log level is `DEBUG`. 
```
MARVIN_VERBOSE=true
```

#### OpenAI
**API key**: Set your OpenAI API key
```
MARVIN_OPENAI_API_KEY=
```
Marvin will also respect this global variable
```
OPENAI_API_KEY=
```

**Model name**: 
Choose the LLM model.
```
MARVIN_LLM_MODEL='gpt-4'
```

#### Database

**Database connection URL**: Set the database connection URL. Must be a fully-qualified URL. Marvin supports both Postgres and SQLite.

```
MARVIN_DATABASE_CONNECTION_URL=
```