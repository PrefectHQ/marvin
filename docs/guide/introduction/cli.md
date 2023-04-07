# CLI

See all available commands:

```shell
marvin --help
```

## TUI

To launch the [TUI](tui.md):
```shell
marvin chat
```

## Bot management

To create a new bot:
```shell
marvin bots create -n MyBot -d "a description of the bot" -p "a personality"
```

To list all bots:
```shell
marvin bots ls
```

To update a bot:
```shell
marvin bots update MyBot -p "a new personality"
```

To delete a bot:
```shell
marvin bots delete MyBot
```
## Database management

```shell
marvin database --help
```

**WARNING**: This will drop all tables and data in the database.
```shell
marvin database reset
```

## Run the server

```shell
marvin server start
```

## Setup OpenAI
    
```shell
marvin setup-openai
```