# CLI
After installation, you can start using `marvin` from the CLI right away.

## Usage
See `marvin --help` for a list of all commands.

### Setup OpenAI Credentials
```bash
marvin setup-openai
```

### Chat with a custom bot
```bash
marvin chat -n SquilliamFancyson -p "Unimpressed, in general. Begrudgingly helpful."
```

### Load and chat with an existing bot
```bash
marvin chat -b my_bot
```

### Start the FastAPI server
```bash
marvin server start
```