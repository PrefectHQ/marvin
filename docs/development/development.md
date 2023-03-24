# Development

## Installing for development

For development, you should clone the git repo and create an editable install. Run the following:

```shell
git clone https://github.com/prefecthq/marvin.git
cd marvin
pip install -e ".[dev]"
```

## Static analysis

In order to merge a PR, code must pass a static analysis check. Marvin uses [`ruff`](https://beta.ruff.rs/docs/) and [`black`](https://black.readthedocs.io/en/stable/) to ensure consistently formatted code. At this time, we do not do a static typing check, but we encourage full type annotation. 

To run the checks locally, you can use [pre-commit](https://pre-commit.com/).

Pre-commit is included as a development dependency. To set it up, run the following from your `marvin` root directory:

```shell
pre-commit install
```

The pre-commit checks will now be run on every commit you make. You can run them yourself with:

```shell
pre-commit run --all-files
```

## Unit tests

Marvin's unit tests live in the `tests/` directory. There are two types of unit tests; those that require LLM calls and those that don't. Tests that require LLM calls should be put in the `tests/llm_tests` directory. They are run separately because they have different time and cost constraints than standard tests.

Marvin uses pytest to run tests. To invoke it:
```shell
# run all tests
pytest

# run only LLM tests
pytest -m "llm"

# run only non-LLM tests
pytest -m "not llm"
```