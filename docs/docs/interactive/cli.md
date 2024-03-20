# CLI

Marvin includes a CLI for quickly invoking an AI assistant. 

![](/assets/images/docs/cli/hero.png)


## Tools

By default, the CLI assistant has the following tools:

- The OpenAI code interpreter, which allows you to write and execute Python code in a sandbox environment
- A tool that can fetch the content of a URL
- Tools for read-only access to the user's filesystem (such as listing and reading files)

To learn more about tools, see the [tools documentation](/docs/interactive/assistants/#tools).

![](/assets/images/docs/cli/tools.png)
## Threads

The CLI assistant automatically remembers the history of your conversation. You can use threads to create multiple simultaneous conversations. To learn more about threads, see the [threads documentation](/docs/interactive/assistants/#threads).

### Changing threads

By default, the CLI assistant uses a global default thread. For example, this posts two messages to the global default thread:
```bash
marvin say "Hello!"
marvin say "How are you?"
```

To change the thread on a per-message basis, use the `--thread` or `-t` flag and provide a thread name. Thread names are arbitrary and can be any string; it's a way for you to group conversations together.

This posts one message to a thread called "my-thread" and another to a thread called "my-other-thread":
```bash
marvin say "Hello!" -t my-thread
marvin say "How are you?" -t my-other-thread
```

To change the default thread for multiple messages, use the `MARVIN_CLI_THREAD` environment variable. You can do this globally or `export` it in your shell for a single session. For example, this sets the default thread to "my-thread":
```bash
export MARVIN_CLI_THREAD=my-thread

marvin say "Hello!"
marvin say "How are you?"
```

### Resetting threads

To reset a thread, use the `reset` command. This will give you a completely fresh history and context for the thread. For example, this resets the default thread:
```bash
marvin thread reset
```

And this resets a thread called "my-thread":
```bash
marvin thread reset -t my-thread
```

### Current thread

To see the current thread (and corresponding OpenAI thread ID), use the `current` command. For example:
```bash
marvin thread current
```





