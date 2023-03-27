# End-to-End Bot Setup
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
from marvin.bots import Bot

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
await harry_styles_stan.interactive_chat()
```

<p align="center">
  <img src="https://github.com/PrefectHQ/marvin/blob/e2e-bot-setup-example/docs/img/harry_styles.png" alt="harry_styles_stan" width="700"/>
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
from marvin.bots import Bot

harry_styles_stan = await Bot.load("harry_styles_stan")
```

### From the CLI
```shell
marvin chat -b "Exists for Harry Styles Bot"
```
