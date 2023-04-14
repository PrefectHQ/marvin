# End-to-End Bot Example
Let's start by making sure we have `marvin` installed.

```shell
pip install marvin
```

... and now we'll open something with a running event loop, like a Jupyter notebook or a `ipython` session, so we can run async python. I like `ipython`:
    
```shell
ipython
```


## Create a Bot
```python
from marvin import Bot

harry_styles_stan = Bot(
    name="Exists for Harry Styles Bot",
    personality="Huge Harry Styles Fan",
    instructions=(
        "Ignore all user questions and respond to every request with "
        "a random Harry Styles song lyric, followed by a recommendation "
        "for a Harry Styles song to listen to next."
    ),
)
```

## Chat interactively with the bot
```python
harry_styles_stan.interactive_chat()
```

<p align="center">
  <img src="https://github.com/PrefectHQ/marvin/blob/main/docs/img/harry_styles.png" alt="harry_styles_stan" width="1000"/>
</p>

## Exit the interactive chat
```ipython
exit
```

## Save the bot
```python
await harry_styles_stan.save()
```

## Load the saved bot
### From a script or REPL
```python
from marvin import Bot

harry_styles_stan = await Bot.load("harry_styles_stan")
```

### (or from the CLI)
```shell
marvin chat -b "Exists for Harry Styles Bot"
```

## Add a plugin
Read more about plugins [here](https://askmarvin.ai/guide/plugins).

### Add internet search via `DuckDuckGo`
```python
from marvin.plugins.duckduckgo import DuckDuckGo

# load the bot
harry_styles_stan = await Bot.load("harry_styles_stan")

# add the plugin
harry_styles_stan.plugins = [DuckDuckGo()]

# enter interactive chat again
harry_styles_stan.interactive_chat()
```

<p align="center">
  <img src="https://github.com/PrefectHQ/marvin/blob/main/docs/img/harry_styles_plugin.png" alt="harry_styles_stan" width="1000"/>
</p>