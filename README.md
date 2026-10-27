![Marvin](docs/assets/img/quotes/it_hates_me.png)

# Marvin

Marvin is a Python library for extracting structured data and running tasks with language models. It builds on [Pydantic AI](https://ai.pydantic.dev/) for model access and adds typed tasks, tools, and conversation history. Made by [Prefect](https://www.prefect.io/).

## Install

Requires Python 3.10 or later and credentials for your model provider.

```bash
uv add marvin
export OPENAI_API_KEY="your-api-key"
```

Marvin uses OpenAI by default. See [model configuration](https://askmarvin.ai/guides/configure-llms) for other providers.

## Use

```python
import marvin
from pydantic import BaseModel

class Contact(BaseModel):
    name: str
    email: str

contacts = marvin.extract("Email Ada at ada@example.com", Contact)
print(contacts)
```

Use `cast` to produce one value, `extract` to find a list of values, `classify` to choose labels, and `generate` to create examples. Each has an async counterpart.

For work that needs instructions, context, or tools, use a task:

```python
import marvin

def stock_level(product: str) -> int:
    """Return the number of units in stock."""
    return {"notebook": 12, "pen": 30}[product]

count = marvin.run(
    "Check how many notebooks are in stock",
    result_type=int,
    tools=[stock_level],
)
```

An `Agent` holds model settings, instructions, and tools you want to reuse. A `Thread` shares conversation history across calls and stores it in a database. See the [quickstart](https://askmarvin.ai/quickstart) and [examples](examples/) for both.

## Develop

```bash
uv sync
uv run pytest tests/basic
uv run pre-commit run --all-files
```

Tests under `tests/ai` make model requests and require provider credentials. Keep test data separate from your local history by setting `MARVIN_HOME_PATH` to a temporary directory.

## Docs

The documentation lives in [docs/](docs/README.md) and is published at [askmarvin.ai](https://askmarvin.ai). See [releases](https://github.com/PrefectHQ/marvin/releases) for changes between versions.

## License

[Apache 2.0](LICENSE).
