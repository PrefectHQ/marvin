# Installation

## Basic Installation

You can install Marvin with `pip`:

```shell
pip install marvin
```

To upgrade to the latest version:

```shell
pip install mavin -U
```

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