# Marvin 🤖🏖️

![](docs/img/heroes/ai_fn_fruits_hero.png)


Meet Marvin: a batteries-included library for building AI-powered software. Marvin's job is to integrate AI directly into your codebase by making it look and feel like any other function. 

Marvin introduces a new concept called [**AI Functions**](https://askmarvin.ai/guide/concepts/ai_functions). These functions differ from conventional ones in that they don’t rely on source code, but instead generate their outputs on-demand with AI by using an LLM as a runtime. With AI functions, you don't have to write complex code for tasks like extracting entities from web pages, scoring sentiment, or categorizing items in your database. Just describe your needs, call the function, and you're done!

AI functions work with native data types, so you can seamlessly integrate them into any codebase and chain them into sophisticated pipelines. Technically speaking, Marvin transforms the signature of using AI from `(str) -> str` to `(**kwargs) -> Any`. We call this **"functional prompt engineering."**

In addition to AI functions, Marvin also introduces more flexible bots. [**Bots**](https://www.askmarvin.ai/guide/concepts/bots.md) are highly capable AI assistants that can be given specific instructions and personalities or roles. They can use custom plugins and leverage external knowledge, and automatically create a history of every thread. Under the hood, AI functions are actually a type of bot. 

Developers can use Marvin to add AI capabilities wherever they will be most impactful, without needing to start from scratch. Marvin's documentation is available at [askmarvin.ai](https://www.askmarvin.ai), and say hello on our [Discord server](https://discord.gg/Kgw4HpcuYG)!
## Features
![](docs/img/heroes/gpp.png)

🪄 Write [AI functions](https://askmarvin.ai/guide/concepts/ai_functions) that process structured data without source code

🤖 Create [bots](https://www.askmarvin.ai/guide/concepts/bots) that have personalities and follow instructions

🔌 Build [plugins](https://askmarvin.ai/guide/concepts/plugins) to give bots new abilities

📚 Store [knowledge](https://askmarvin.ai/guide/concepts/loaders_and_documents) that bots can access and use

📡 Available as a Python API, interactive CLI, or FastAPI server

## Quick start
1. **Install**: `pip install marvin`
2. **Chat**: `marvin chat`

```shell
marvin chat -p "knows every Star Wars meme" Hello there
```
![](docs/img/marvin_hello_there_chat.png)


See the [getting started](https://www.askmarvin.ai/getting_started/installation/) docs for more!

## Open Source

Marvin is open-source with an Apache 2.0 license and built on standards like Pydantic, FastAPI, Langchain, and Prefect.

### 🚧 Construction Zone

Marvin is under active development and is likely to change.

Coming soon:

♻️ Interactive AI functions

🖼️ Admin and chat UIs

🏗️ Advanced data loading and preprocessing

🔭 AI observability platform

🖥️ Deployment guides

🎁 Quickstarts for common use cases



## When should you use Marvin?

Marvin is an opinionated, high-level library with the goal of integrating AI tools into software development. There are a few major reasons to use Marvin:

1. **You want an [AI function](https://askmarvin.ai/guide/concepts/ai_functions) that can process structured data.** Marvin brings the power of AI to native data structures, letting you build functions that would otheriwse be difficult or even impossible to write. For example, you can use AI functions to make a list of all the animals in a paragraph, generate JSON documents from HTML content, extract keywords that match some criteria, or categorize sentiment -- without any traditional source code.

2. **You want an [AI assistant](https://askmarvin.ai/guide/concepts/bots) in your code.** Marvin's bots can follow instructions and hold conversations to solve complex problems. They can use custom plugins and take advantage of external knowledge. They are designed to be integrated into your codebase, but of course you can expose them directly to your users as well!

3. **You want to deploy cutting-edge AI technology with confidence, but without having to make too many decisions.** Using LLMs successfully requires very careful consideration of prompts, data preprocessing, and infrastructure. Our target user is more interested in *using* AI systems than *building* AI systems. Therefore, Marvin is designed to make adopting this technology as straightforward as possible by optimizing for useful outcomes. Marvin's prompts have been hardened by months of real-world use and will continue to improve over time.
## When should you NOT use Marvin?
There are a few reasons NOT to use Marvin:

1. **You want full control of the AI.** Marvin is a high-level library and (with few exceptions) does not generally expose LLM configuration to users. We have chosen settings that give the best results under most circumstances, taking Marvin's built-in prompts into consideration.

2. **You want an AI copilot for writing code.** Marvin's job isn't to help you write source code; it's to help you do things that are difficult or impossible to express in source code. That could range from mundane activities to writing a function that can extract the names of animals commonly found in North America from an email (yes, it's a ridiculous example - but it's possible). Modern LLMs excel at complex reasoning, and Marvin lets you bring that into your code in a way that feels native and natural.
   
3. **You want to use other LLM models.** Marvin is designed to run against OpenAI's GPT-4 and GPT-3.5 models. While we may expand those models in the future, we've discovered that prompts designed for one model rarely translate well to others without modification. In order to maximize the usefulness of the library, we've decided to focus on just these popular models for now.

4. **You want full control of your prompts.** As a "functional prompt engineering" platform, Marvin takes user inputs and generates prompts that are likely to deliver the outcome the user wants, even if they are not verbatim what the user said. Marvin does not expect users to send completely raw prompts to the LLM. 
 
5. **You're searching for the Ultimate Question.** While Marvin is highly intelligent, even he couldn't come up with the Ultimate Question of Life, the Universe, and Everything. If you're seeking existential enlightenment, you might need to look beyond our beloved paranoid android.

