# Installation

![](../../img/heroes/pip_install_marvin_hero.png)

## Basic Installation

You can install Marvin with `pip` (note that Marvin requires Python 3.9+):

```shell
pip install marvin
``` 

To verify your installation, run `marvin --help` in your terminal. 

You can upgrade to the latest released version at any time:

```shell
pip install marvin -U
```

!!! warning "Breaking changes in 1.0"
    Please note that Marvin 1.0 introduces a number of breaking changes and is not compatible with Marvin 0.X.

## Adding Optional Dependencies
Marvin's base install is designed to be as lightweight as possible, with minimal dependencies. To use functionality that interacts with other services, install Marvin with any required optional dependencies. For example:

```shell
# dependencies for running Marvin as a slackbot
pip install 'marvin[slackbot]'
```


## Installing for Development
See the [contributing docs](/src/development_guide/) for instructions on installing Marvin for development.
