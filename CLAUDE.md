# Working on Marvin

Use `uv` for dependencies and Python commands. Use `X | Y`, built-in collection types, and type annotations for new Python code.

```bash
uv sync
uv run pytest tests/basic
uv run pre-commit run --all-files
```

`tests/basic` does not call LLM providers. `tests/ai` makes real model requests. Set `MARVIN_HOME_PATH` to a temporary directory when testing so database and memory tests do not use local data.

The Slack bot is a separate workspace package under `examples/slackbot`; read its instructions before changing it. Library work should not require bot dependencies or changes to its deployment.

Edit handwritten documentation in `docs/`. API reference pages are generated from Python signatures and docstrings:

```bash
uv run scripts/create_mintlify_api_ref.py
```

Run the generator after source documentation changes. Keep examples executable, describe actual return types, and check claims against the implementation. Generated examples are not evidence that an API exists.

Use the ignored `repros/` directory for issue reproductions. Public API changes, dependency migrations, and release procedures need their own review; keep cleanup changes focused.
