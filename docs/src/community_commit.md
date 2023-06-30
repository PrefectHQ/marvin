# Contribute to Marvin

## Prerequisites
Marvin requires [Python 3.9+](https://www.python.org/downloads/).

## Installation
Clone a fork of the repository and install the dependencies:
```bash
git clone https://github.com/youFancyUserYou/marvin.git
cd marvin
```

Activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate
```

Install the dependencies in editable mode:
```bash
pip install -e ".[dev]"
```

Install the pre-commit hooks:
```bash
pre-commit install
```

## Testing
Run the tests that don't require an LLM:
```bash
pytest -vv -m "not llm"
```

Run the LLM tests:
```bash
pytest -vv -m "llm"
```

Run all tests:
```bash
pytest -vv
```

## Opening a Pull Request
Fork the repository and create a new branch:
```bash
git checkout -b my-branch
```

Make your changes and commit them:
```bash
git add . && git commit -m "My changes"
```

Push your changes to your fork:
```bash
git push origin my-branch
```

Open a pull request on GitHub - ping us [on Discord](https://discord.gg/Kgw4HpcuYG) if you need help!