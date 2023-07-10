# Installation

## Basic Installation


You can install Marvin with `pip`:

```shell
pip install marvin
```

Please note that Marvin requires Python 3.9+. 

Verify your installation:

```bash
marvin --help
```

Upgrade to the latest version:

```shell
pip install mavin -U
```

!!! warning "Breaking changes in 1.0"
    Please note that Marvin 1.0 introduces a number of breaking changes and is not compatible with Marvin 0.x code.
## Configuration


Marvin uses the OpenAI API to access state-of-the-art language models, including GPT-4 and GPT-3.5. Note that Marvin uses the `gpt-3.5-turbo` model by default. In order to use the OpenAI API, you must provide an API key.

### Getting an API key
To obtain an OpenAI API key, follow these steps:

1. [Log in](https://platform.openai.com/) to your an OpenAI account (sign up if you don't have one)
2. Go to the "API Keys" [page](https://platform.openai.com/account/api-keys) under your account settings.
3. Click "Create new secret key." A new API key will be generated. Make sure to copy the key to your clipboard, as you will not be able to see it again.


### Setting the API key
Alternatively, you can provide your API key as an environment variable (as with any Marvin setting). Marvin will check `MARVIN_OPENAI_API_KEY` followed by `OPENAI_API_KEY`. The latter is more standard and may be accessed by multiple libraries, but the former can be used to scope the API key for Marvin's use only. These docs will use `MARVIN_OPENAI_API_KEY` but either will work.

To set your OpenAI API key as an environment variable, open your terminal and run the following command, replacing <your API key> with the actual key:
```shell
export MARVIN_OPENAI_API_KEY=<your API key>
```

This will set the key for the duration of your terminal session. To set it more permanently, configure your terminal or its respective env files.

You can find out more about configuring `marvin` [here](reference/configuration.md).


## Adding Optional Dependencies
Marvin's base install is designed to be as lightweight as possible, with minimal dependencies. To use functionality that interacts with other services, install Marvin with any required optional dependencies:

```shell
# dependencies for running Marvin as a slackbot
pip install marvin[slackbot]

# dependencies for running Marvin with lancedb
pip install marvin[lancedb]
```


## Installing for Development

To install Marvin for development, or to run against the most bleeding-edge version, clone the repo and create an editable installation including all development dependencies:

```shell
git clone https://github.com/prefecthq/marvin
cd marvin
pip install -e ".[dev]"
```