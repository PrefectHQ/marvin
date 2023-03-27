# Welcome to Marvin 🤖🏖️

![](ai_fn_demo.png)

Marvin is a batteries-included library designed to simplify the process of building AI-powered software. It introduces three core abstractions: AI functions, bots, and Knowledge. AI functions are powerful tools that let users define and execute functions without any source code, while bots serve as AI assistants that can follow instructions and use plugins. Knowledge provides an effective method for enhancing bots' abilities by loading external information. Marvin's innovative approach to "functional prompt engineering" allows developers to work with structured inputs and outputs, seamlessly integrating AI functions into traditional code and enabling the creation of sophisticated AI pipelines.


> "Let’s build robots with Genuine People Personalities," they said. So they tried it out with me. I’m a personality prototype. You can tell, can’t you?
>
> -- [Marvin](https://www.youtube.com/clip/UgkxNj9p6jPFM8eWAmRJiKoPeOmvQxb8viQv)


## Features


🦾 Write [AI functions](guide/ai_functions.md) that process structured data without source code

🤖 Create [bots](guide/bots.md) that have personalities and follow instructions

🔌 Build [plugins](guide/plugins.md) to give bots new abilities

📚 Store [knowledge](guide/loaders_and_documents.md) that bots can access and use

📡 Available as a Python API, interactive CLI, or FastAPI server

## Quick start
1. **Install**: `pip install marvin`
2. **Chat**: `marvin chat`

```shell
marvin chat -p "knows every Star Wars meme" Hello there
```
<img width="1034" alt="image" src="https://user-images.githubusercontent.com/153965/226232390-c98ffee3-c272-42fa-befb-70d94bebfda7.png">


See [getting started](getting_started/installation.md) for more!

## Highlights

🔋 Batteries included - get up and running instantly

🧑‍🎓 Powered by GPT-4 (or GPT-3.5)

🌈 Supports ChromaDB, SQLite, and Postgres

Coming soon:

💬 Persistent threads with multiple bots

🖼️ Admin and chat UIs

🔭 AI observability platform

## When should you use Marvin?

Marvin is an opinionated, high-level library with the goal of integrating AI tools into software development. There are two major reasons to use Marvin:
1. You want an [AI function](guide/ai_functions.md) that can process structured data. This is especially useful for string processing when regex just won't cut it ("Give me a list of all the animals in this paragraph"; "Extract the account details from this web page into JSON"; "Categorize the sentiment of these comments") but can work with many other types of data as well.
2. You want an [AI assistant](guide/bots.md) in your code. Marvin's bots use prompts that have been hardened by months of real-world use and will continue to improve over time. They are designed to be called from code, though of course you may want to expose them directly to your users as well!



