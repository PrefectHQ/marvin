# Installation

![](../img/heroes/dont_panic.png)


## Requirements

Marvin requires Python 3.9+.
## For normal use
To install Marvin, run `pip install marvin`. As a matter of best practice, we recommend installing Marvin in a [virtual environment](https://realpython.com/python-virtual-environments-a-primer/).

To use Marvin's [knowledge features](../guide/concepts/infra.md), please include the [Chroma](https://www.trychroma.com/) dependency: `pip install "marvin[chromadb]"`.

Marvin uses OpenAI's GPT-3.5 (ChatGPT) model by default. Before using Marvin, you'll need to provide an [OpenAI API key](guide/introduction/configuration/#openai) (via the the `MARVIN_OPENAI_API_KEY` or `OPENAI_API_KEY` environment variables) or choose a [different LLM backend](/guide/introduction/configuration#selecting-an-llm-backend).

## For development

To install Marvin for development, please see the [development guide](../development/development.md).
