# Getting Setup

Marvin requires Python 3.9+.

## Installation
`marvin` is available on PyPI and can be installed via `pip`:

```bash
pip install -U marvin
```
!!! tip "Verify your installation"
    ```bash
    marvin --help
    ```

Note that `marvin<1.0.0` is incompatible with `marvin>=1.0.0`.

## Configuration
`marvin` needs an LLM to talk to.

Set an `OPENAI_API_KEY` environment variable on your machine:

!!! tip "Verify your API key is set"
    ```bash
    python -c "import marvin; print(marvin.settings.openai_api_key.get_secret_value())"
    ```

You can find out more about configuring `marvin` [here](reference/configuration.md).