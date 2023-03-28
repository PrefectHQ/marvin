# Development

<!-- ![](incredible_even_worse_hero.png) -->
![](../img/hero_code/end_in_tears_hero.png)
## Installing for development

For development, you should clone the [git repo](https://github.com/prefecthq/marvin) and create an editable install including all development dependencies. To do so, run the following:

```shell
git clone https://github.com/prefecthq/marvin.git
cd marvin
pip install -e ".[dev]"
```

Please note that editable installs require `pip >= 21.3`. To check your version of pip, run `pip --version` and, if necessary, `pip install -U pip` to upgrade.

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