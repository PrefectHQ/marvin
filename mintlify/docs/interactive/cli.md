# CLI

Marvin includes a CLI for quickly invoking an AI assistant.

![](/assets/images/docs/cli/hero.png)

To use the CLI, simply `say` something to Marvin:

```bash
marvin say "hi"
```

You can control the [thread](#threads) and [assistant](#custom-assistants) you're talking to, as well as the [LLM model](#models) used for generating responses.

### Chat mode

By default, the CLI responds to a single message, then exits. To continue your conversation, you must reinvoke the CLI (possibly with the same arguments). Marvin also has a "chat mode" that allows you to have an extended conversation. Pass the `--chat` or `-c` flag to do this:

```bash
marvin say "hi" -c
```

In chat mode, the CLI will continue to prompt you for messages until you exit by typing `exit` or pressing `Ctrl+C`.

## Models

By default, the CLI uses whatever model the assistant is configured to use. However, you can override this on a per-message basis using the `--model` or `-m` flag. For example, to use the `gpt-3.5-turbo` model for a single message:

```bash
marvin say "hi" -m "gpt-3.5-turbo"
```

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

### Clearing threads

To reset a thread and clear its history, use the `clear` command. For example, this clears the default thread:

```bash
marvin thread clear
```

And this clears a thread called "my-thread":

```bash
marvin thread clear -t my-thread
```


### Current thread

To see the current thread (and corresponding OpenAI thread ID), use the `current` command. For example:

```bash
marvin thread current
```

## Custom assistants

The Marvin CLI allows you to register and use custom assistants in addition to the default assistant. Custom assistants are defined in Python files and can have their own set of instructions, tools, and behaviors.

Using a custom assistant has the following workflow:

1. Define the assistant in a Python file
2. Register the assistant with the Marvin CLI
3. Use the assistant in the CLI

### Defining an assistant

To use a custom assistant, you must define it in a Python file. In a new file, create an instance of the `Assistant` class from the `marvin.beta.assistants`. Provide it with any desired options, such as a name, instructions, and tools. To learn more about creating assistants, see the [assistants documentation](/docs/interactive/assistants/). The only requirement is that the assistant object must be assigned to a global variable in the file so that the CLI can load it.

For example, this file defines an assistant named "Arthur" that can use the code interpreter. The assistant is stored under the variable `my_assistant`.

```python
# path/to/custom_assistant.py

from marvin.beta.assistants import Assistant, CodeInterpreter

my_assistant = Assistant(
    name="Arthur",
    instructions="A parody of Arthur Dent",
    tools=[CodeInterpreter]
)
```

### Registering an assistant

Once you've created a Python file that defines an assistant, you can register it with the Marvin CLI. This allows you to use the assistant in the CLI by name.

To do so, use the `marvin assistant register` command followed by the fully-qualified path to the Python file *and* the variable that contains the assistant. For example, to register the assistant defined in the previous step, use the following command:

```bash
marvin assistant register path/to/custom_assistant.py:my_assistant
```

This command will automatically use the assistant's name (Arthur) as the name of the assistant in the Marvin CLI registry. You will need to provide the name to load the assistant, which is why each registered assistant must have a unique name. Registering an assistant with the same name as an existing one will fail. In this case, you can either delete the existing assistant or use the `--overwrite` or `-o` flag to overwrite it. You can also provide an alternative name during registration using the `--name` or `-n` flag. For example, this would register the assistant with the name "My Custom Assistant":

```bash
marvin assistant register path/to/custom_assistant.py:my_assistant -n "My Custom Assistant"
```


!!! warning 
    When you register an assistant, its name and the path to the file that contains it are stored in the Marvin CLI registry. This allows the CLI to load the assistant whenever you need it. However, it means the assistant file **must** remain in the same location, with the same name, for the CLI to find it. If you move or rename the file, you will need to re-register the assistant. However, if you edit the file without changing the variable name of the assistant, the CLI will automatically use the updated assistant.



### Using an assistant

To use a custom assistant when sending a message, use the `--assistant` or `-a` flag followed by the name of the registered assistant. For example, if you registered an assistant named "Arthur", you can talk to it like this:

```bash
marvin say "Hello!" -a "Arthur"
```

You can also set a default assistant using the MARVIN_CLI_ASSISTANT environment variable, similar to setting a default thread. This allows you to set a global or session-specific default assistant.

#### Mixing threads and assistants

Threads and assistants are independent, so you can talk to multiple assistants in the same thread. Note that due to limitations in the OpenAI API, assistants aren't aware of other assistants, so they assume that they said everything in the thread history (even if another assistant did).

```bash
marvin say "Hello!" -a "Arthur" -t "marvin-thread"
```

### Listing registered assistants

To see a list of all registered assistants, use the `marvin assistant list` command. This will display a table with the names and file paths of the registered assistants.

### Deleting a registered assistant

To remove a registered assistant, use the `marvin assistant delete` command followed by the name of the assistant. For example:

```bash
marvin assistant delete "My Custom Assistant"
```

Note that this only removes the reference to the assistant in the Marvin registry and does not delete the actual assistant file, even if you used the `--copy` flag during registration.
