Marvin 3 Documentation Plan

Structured Sitemap

The documentation will be organized into clear sections and pages to cater to both newcomers and experienced users. The structure (inspired by ControlFlow’s documentation hierarchy ￼) will include introductory material, core concept explanations, how-to guides for common tasks, advanced topics for multi-modal capabilities, integration/CLI usage, configuration, and a migration guide. Below is the proposed sitemap:
	•	Introduction
	•	What is Marvin 3? – Overview of Marvin’s purpose and core philosophy (lightweight AI toolkit, agentic workflow, reliability) ￼ ￼. Highlights of Marvin 3’s new features and improvements.
	•	Installation & Setup – Step-by-step installation instructions (using pip, etc.) ￼ and initial configuration (setting API keys, provider setup ￼).
	•	Quickstart – A minimal example of Marvin in action. Shows how to run a simple task with one line (marvin.run) ￼ and get an immediate result. Introduce main entry point and confirm everything is working.
	•	Tutorial: Building a Multi-step Workflow – A guided tutorial that walks the user through building a small application using Marvin. For example, prompt the user for input, use Marvin to plan tasks, research information, and produce a final output (as demonstrated in the Marvin “Workflow Example” ￼ ￼). This ties together threads, tasks, and agents in a realistic scenario.
	•	Core Concepts
	•	Tasks – Explanation of Marvin’s fundamental unit of work. Describe how each task has an objective (instructions) and produces a type-safe result ￼. Cover creating tasks with marvin.Task (and via marvin.run for simplicity), using result_type to enforce structured outputs (e.g. Pydantic models for type safety), and how tasks can utilize context and tools for more complex objectives ￼ ￼. Emphasize that tasks are objective-focused, tool-enabled, observable, and composable ￼. Include examples of simple tasks and a task using a custom tool and context.
	•	Agents – Describe what an Agent is in Marvin (an LLM configuration with a role/persona) and how agents execute tasks ￼ ￼. Explain creating an agent with custom instructions, optional model selection, and parameters (e.g. using Anthropic or other provider models) ￼. Show how an agent can be reused across tasks and how multiple agents can collaborate. Emphasize that agents are specialized, portable, collaborative, and customizable ￼. Provide code examples, such as creating an agent and assigning it a task (agent.run("prompt")).
	•	Threads (Workflows) – Introduce Marvin’s mechanism for orchestrating tasks. Explain the marvin.Thread context manager (formerly “Flow” in ControlFlow) for grouping tasks so they share state ￼. Show how threads maintain conversation history and context across multiple marvin.run calls, enabling workflows where each step builds on previous outputs ￼ ￼. Highlight that threads allow dependent tasks and persistent memory (history stored, e.g. in SQLite by default ￼). Provide an example of using with marvin.Thread(): ... to run a sequence of tasks manually.
	•	Tools and Context – Explain how to extend Marvin’s capabilities by giving tasks access to custom Python functions (tools) and external data. Define what a “tool” is (similar to ControlFlow tools ￼ ￼) – essentially a Python function that an agent can call to perform actions beyond the LLM’s native scope. Detail how to pass tools=[...] and context={...} to tasks or agents ￼ ￼, and how Marvin uses type hints and docstrings to guide the agent in using tools effectively. Include best practices for writing tools (clear function name, docstring instructions, type hints) ￼ ￼. Provide a simple example (e.g., a task that uses a run_shell_command tool to get system info ￼ ￼).
	•	Memory – Discuss how Marvin handles conversation memory and state. Explain that Marvin automatically records task history and agent interactions so context can be carried forward (this is largely handled via Threads and the marvin.Memory backend). Mention that Marvin 3 stores message history in a SQLite database by default ￼, ensuring persistence between runs (and how to configure it, e.g., in-memory for dev). Show how an agent or thread can retrieve past info (implicitly done for users, but mention any APIs if relevant, like a marvin.Memory object or how to limit memory). If applicable, describe options to configure memory (like environment variables or using a different memory provider, analogous to ControlFlow’s memory providers).
	•	AI Functions (Decorators) – Introduce the @marvin.fn decorator for creating custom AI-powered functions ￼. Explain that this allows developers to write a Python function signature with type annotations and docstring, and have Marvin generate the implementation using an LLM ￼. Essentially, Marvin turns the function into a prompt using the types and docstring as context. Provide an example of defining a simple AI function (e.g., @marvin.fn def translate(text: str, language: str) -> str: """Translate text to the given language.""") and show how calling it executes an LLM under the hood to return a result. Emphasize how this abstracts prompt writing and yields self-documenting AI capabilities.
	•	Multi-Agent Teams – Cover advanced use-cases with multiple agents working together. Define what a Team is and how it allows agents (or even other teams) to delegate tasks amongst each other ￼. Introduce Swarm, a specific type of team where all agents can cooperate freely (Swarm = all-agents team) ￼ ￼. Provide a code example of creating a Swarm of agents and running a task that they all participate in (as shown in the Marvin 3 release notes ￼ ￼). Explain scenarios where multi-agent setups are useful (e.g., complex tasks that benefit from specialized roles like “Writer”, “Editor”, “Fact-Checker” working together ￼ ￼). Also clarify the difference between using a team vs a single agent for a task.
	•	How-To Guides (Common Tasks)
These pages offer step-by-step guidance and examples for common tasks LLM developers will perform with Marvin’s high-level API functions. Each page will include a description of the function, parameters, and a concrete example with code and output.
	•	Summarize Text – How to get quick summaries of text using marvin.summarize ￼. Outline when to use it (e.g., condense long articles or outputs). Provide an example of calling marvin.summarize(long_text) and show an excerpt of the input and the summary output. Discuss any options like adjusting length or style if available (or guidance to feed instructions).
	•	Classify Data – Using marvin.classify to categorize text or data into predefined labels ￼. Show how to supply possible categories (list of labels, enums, etc.) for classification. Provide an example, such as classifying a user query into categories like FAQ vs Feedback. Cover how the result is returned (likely the chosen label or an index) and how Marvin ensures one of the provided classes is selected. Mention best practices (clear category definitions to the model).
	•	Extract Information – Guide for marvin.extract, which pulls structured info from unstructured text ￼. Explain that you can specify a target type or schema (like a Python type or Pydantic model) and Marvin will extract matching data. Use an example from the README: extracting integers (monetary amounts) from a sentence ￼ ￼. Show how the output comes as a Python object (list, dict, etc.) and note how this helps enforce correctness.
	•	Transform Data Types – How to use marvin.cast to transform unstructured input into a specific structured type ￼. For example, provide a location name and cast it to a coordinates dict or custom model (as in the README example converting “the place with the best bagels” into a Location TypedDict with lat/long ￼). Demonstrate usage and explain how Marvin figures out the structure from the type annotations.
	•	Generate Data or Content – Using marvin.generate to create structured data based on a description ￼. Explain that this can produce a list or set of results of a given type. For instance, show generating a list of prime numbers or sample data given a prompt (e.g., marvin.generate(int, 10, "odd primes") returning a list of primes ￼). Also mention generating text content in a structured way if applicable.
	•	Conversational AI (Chat) – How to have interactive conversations using Marvin. Introduce marvin.say for LLM-driven conversation or chat responses ￼. Provide an example of using marvin.say("Hello, how can I help you today?") to get a friendly response, or how to maintain a back-and-forth dialog using threads (for context) and repeated calls. Highlight that marvin.say is a quick way to get an LLM reply as if chatting. Optionally, show how to customize the “persona” or style of the assistant (perhaps via an Agent with certain instructions, then using that agent for conversation). This guide should address how Marvin can be used to build chatbots or assistant-like interactions, which is a common use-case for those coming from other frameworks.
	•	Working with Other Modalities (For completeness, Marvin supports AI tasks beyond text; these pages will cover usage for images, audio, etc., likely leveraging underlying models via Pydantic AI or API integrations.)
	•	Generate Images – Guide for creating images from text prompts (e.g., via Stability AI or DALL-E integration). Show how to call Marvin’s image generation function (e.g., marvin.ai.images.create_image("A cat riding a bicycle")) and what kind of object or URL is returned. Include an example and note any prerequisites (API keys for image models) and parameters (size, style hints, etc.).
	•	Caption Images – Using Marvin to generate captions or descriptions for given images. Explain how to provide an image (file path or URL) to Marvin’s caption function and get a text description. Provide a quick example (ensuring to describe the input method since this might not be pure text input). Mention use cases (automatically describing images).
	•	Extract Data from Images – If Marvin can extract text (OCR) or identify entities from images, document how to do so. For example, using Marvin to find objects or text in an image. Provide an example if available (like extracting text from a screenshot or identifying objects).
	•	Classify Images – Show how Marvin can classify images into categories (if supported via an image model). E.g., feeding an image and getting a label like “cat” or “dog”. Detail how to supply the categories or if it uses a default classifier.
	•	Generate Speech (Text-to-Speech) – Guide for converting text to spoken audio using Marvin’s audio capabilities (if any, e.g., calling marvin.ai.audio.generate_speech("Hello") to get an audio file). Include example code and how to play or retrieve the audio output.
	•	Transcribe Speech (Speech-to-Text) – How to use Marvin to transcribe audio into text (via marvin.ai.audio.transcribe_speech(audio_file) presumably). Provide an example of transcribing a short audio clip and show the resulting text.
	•	Record Audio – If Marvin provides utilities to record audio via microphone or generate audio files, document the usage. For instance, starting a recording session or saving audio input for processing (as indicated by Marvin 2’s docs). Example: how a developer might capture audio from a user and then use Marvin to transcribe it.
	•	Record Video – Document any functionality to capture or handle video (Marvin 2 had a stub for recording video). If Marvin 3 supports this (perhaps as part of an example application), provide instructions, otherwise note if this is a placeholder/experimental.
	•	Interactive Tools & Integration
	•	Assistants (Persistent Agents) – Show how to build a long-running assistant or chatbot that retains context across multiple interactions (for example, a Slack bot or a CLI assistant). This guide can combine Agents, Threads, and Memory: instruct how to set up an Agent with a persona (e.g. a helpful assistant), possibly connect it to a chat interface or loop. Use the Slackbot example from Marvin 2’s cookbook as inspiration (updated for Marvin 3). Outline how to handle user input continuously, how to store conversation state (using threads or memory), and how to respond. Emphasize Marvin’s lightweight approach to this compared to heavier frameworks (no complex DAG or callback setup needed).
	•	Command-Line Interface (CLI) – Document any CLI tool or commands that come with Marvin (if Marvin provides a CLI entry point). For example, using marvin from the shell to run tasks or chat. If Marvin 3 does not have a separate CLI tool, demonstrate how to achieve CLI interaction using Python (like using cli=True in marvin.run to prompt the user ￼). Essentially, guide users who prefer command-line interactions on how to use Marvin for quick tasks or interactive sessions.
	•	Applications & Integration – Provide guidance on embedding Marvin into larger applications or integrating with other systems. This could include how to use Marvin within a web server (for instance, integrating with FastAPI or Flask to serve an AI endpoint), or how to schedule Marvin tasks in workflows (Prefect integration, given Marvin’s ties to Prefect/ControlFlow). Include any best practices for using Marvin in production (error handling, retries, using libraries like Tenacity for robustness – if relevant mention) and how to keep the system lightweight (only use what you need). This page can also link out to community examples or the Cookbook for specific integrations.
	•	Configuration & Reference
	•	Settings & Environment Variables – Detailed reference of configuration options. List out important environment variables (e.g., OPENAI_API_KEY, MARVIN_DATABASE_URL, etc.) and how they affect Marvin’s behavior ￼ ￼. Explain how to configure default settings through marvin.settings (if a Pythonic config exists) or .env files. For example, how to set a default model globally, adjust logging levels, or toggle dev/test modes. Ensure this page consolidates all the knobs a developer can turn to configure Marvin to their needs (similar to Marvin 2’s Settings page).
	•	Model Providers – Guide on using different LLM providers and models with Marvin. Explain that Marvin 3 leverages Pydantic AI to support many models out-of-the-box ￼. Provide instructions for popular providers: e.g., how to use Azure OpenAI (setting API endpoint keys), how to use Anthropic (as shown with AnthropicModel in an Agent example ￼), Hugging Face, etc. If using certain providers requires additional packages or model identifiers, outline those steps. Also, describe how to specify a model at runtime (marvin.run(prompt, model=...) or via Agent config) and mention the default model (likely OpenAI GPT-4 or similar) ￼. This page will help users who are transitioning from other toolkits where model switching might have been complex; show that in Marvin it’s straightforward to use any supported model.
	•	Memory & Storage Configuration – (If not fully covered under Settings) explain how to configure Marvin’s memory store. E.g., using an in-memory setting for ephemeral usage vs persistent database for long-term memory ￼. If Marvin allows pluggable memory backends (like different databases or vector stores for long-term memory), document how to set those up. If not, at least explain how to manage the SQLite file or how to clear it if needed. Include any relevant settings for controlling memory (like max history length, etc., if exposed).
	•	Logging & Debugging – (Optional) Describe how Marvin logs its operations and how users can enable debug mode or view detailed traces of agent decisions. For example, mention that Marvin prints structured logs of tool usage and task steps (as shown in examples where agent actions are displayed in a box ￼). Advise on using these logs to diagnose issues, and how to increase verbosity if needed. If Marvin integrates with any monitoring (like Prefect’s Orion or other), mention that as well.
	•	Cookbook & Examples
(A collection of stand-alone examples and recipes to solve specific problems with Marvin. Each of these will be a tutorial-style page focusing on a use-case.)
	•	Migration: Slackbot Assistant – Update the Marvin 2 Slackbot example ￼ for Marvin 3. Show how to build a Slack (or Discord, etc.) chatbot that listens for messages and responds using Marvin. Include steps for connecting to Slack’s API, using a Marvin agent to generate responses, and maintaining context per conversation. Highlight how lightweight the solution is (no need for extensive infrastructure).
	•	Data Deduplication with AI – From Marvin 2’s “Entity deduplication” recipe, demonstrate how to use Marvin to identify and merge duplicate entries in data. For example, feed a list of slightly varying records (names, etc.) to Marvin’s extract or classify functions to cluster duplicates. Show how the structured output ensures clean merging.
	•	Augmenting Prompts with Code – Based on “Python augmented prompts” example, illustrate how Marvin can be combined with Python code for powerful results. E.g., use Marvin to generate a query, run that query against an API or database with Python, then feed results back into Marvin for a final answer. This shows interplay of Marvin with external tools and data (reinforcing how Marvin “gets out of the way” for developers ￼).
	•	Type-Specific Prompting – Based on “Being specific about types”, give examples of how providing precise Pydantic models or types to Marvin yields better outputs. Perhaps demonstrate a scenario with and without type guidance to show the difference in output quality or reliability.
	•	Additional Examples – (Placeholder for any other relevant recipes, like integrating Marvin with web scraping, creating a Q&A bot with context from documents, etc. These can be added as needed, ensuring a broad range of use-cases is covered.)
	•	Migration Guide
	•	Upgrading to Marvin 3.0 – A dedicated page for existing Marvin 2.0 or ControlFlow users transitioning to Marvin 3. Start with a brief overview of Marvin 3’s backward compatibility and changes ￼. Include Key Changes in bullet form (as in the release notes): e.g., “Flow” renamed to Thread ￼, removal of @flow decorator, new marvin.Task/marvin.Agent replacing ControlFlow’s classes ￼ ￼, adoption of Pydantic AI (instead of LangChain) ￼, and the new SQLite-based memory backend ￼. Provide side-by-side code snippets if possible: old way vs new way for common patterns (especially for ControlFlow users, show how cf.run/Flow translates to marvin.run/Thread usage).
	•	New Features in Marvin 3 – Highlight what’s new or improved, so upgraders know what additional capabilities they can leverage. This includes Swarms/Teams for multi-agent collaboration ￼ ￼, new high-level functions like summarize and say ￼, and improved integration of Marvin’s functions into workflows (thanks to the unified engine). Also mention any features from 2.0 that were removed or are not yet available (e.g. streaming outputs not yet supported ￼). This section ensures users don’t overlook the upgrades that can simplify their work (like built-in planning via marvin.plan etc.).
	•	Common Pitfalls for Migrators – (If applicable) enumerate any known issues or differences that might surprise users coming from Marvin 2 or ControlFlow. For example, note that Marvin’s API is largely similar but some defaults or behaviors might differ (maybe memory persistence, or how tasks are executed immediately vs deferred). Advise on testing existing code thoroughly and refer to this guide for adjusting code. Encourage users that Marvin 3 aims to “combine the DX of Marvin 2.0 with the powerful agentic engine of ControlFlow” ￼, meaning they get the best of both in one toolkit.

(The sitemap above ensures logical navigation: a newcomer can start at Introduction and Getting Started, then learn core concepts in a sensible order, proceed to practical guides, and explore advanced capabilities. Experienced users can jump directly to specific guides or reference pages as needed. All pages are interlinked where appropriate for easy cross-referencing.)

Detailed Content for Each Page

Below, we define the focus of each documentation page and provide a full prompt that can be used to generate high-quality content for that page. Each prompt is crafted to ensure the tone and clarity align with Marvin’s style and that all essential information (drawn from source material and Marvin’s features) is covered.

Introduction – What is Marvin 3?

Summary: This page introduces Marvin 3 and sets the stage for the documentation. It should explain what Marvin is (a lightweight AI engineering toolkit), who it’s for (LLM application developers), and what problems it solves. Emphasize Marvin’s lightweight nature and contrast it with “bloated toolkits” – meaning Marvin avoids unnecessary complexity and focuses on developer joy and productivity ￼. Mention Marvin 3’s lineage: it combines the ease-of-use of Marvin 2 with the agentic workflow engine of ControlFlow ￼. Highlight key capabilities (task-oriented design, specialized agents, type-safe outputs, multi-agent orchestration) as bullet points to entice the reader ￼. The tone should be enthusiastic and welcoming, conveying that “working with AI should spark joy” ￼. Include a very simple code snippet (maybe the one-line marvin.run("Write a short poem about X")) to give a quick taste of usage ￼. Keep the content high-level and inspiring, setting up motivation to use Marvin.

Prompt:

You are an AI documentation writer tasked with drafting the **"What is Marvin 3?"** page for Marvin's documentation. 

Write an engaging introduction that welcomes readers and clearly explains Marvin 3's purpose and benefits. Start by defining Marvin in one sentence (e.g. "Marvin is a lightweight AI engineering toolkit for building natural language interfaces...") [oai_citation_attribution:74‡askmarvin.ai](https://askmarvin.ai/#:~:text=The%20AI%20Engineering%20Toolkit). 

In the opening paragraph, emphasize Marvin's lightweight, developer-friendly nature and its focus on reliable, scalable AI workflows (contrast this with heavy, bloated frameworks without naming them, to reassure readers that Marvin is simpler). 

Next, in a short paragraph, mention that Marvin 3 builds on the strengths of Marvin 2.0 and Prefect's ControlFlow [oai_citation_attribution:75‡pypi.org](https://pypi.org/project/marvin/3.0.0/#:~:text=Marvin%203,in%20particular%20for%20ControlFlow%20users) – so both existing Marvin users and ControlFlow users will find familiar elements. Explain the concept of "agentic AI workflows" in simple terms (delegating tasks to AI agents, orchestrating multi-step processes) as Marvin’s core idea [oai_citation_attribution:76‡github.com](https://github.com/PrefectHQ/marvin#:~:text=Marvin%20is%20a%20Python%20framework,for%20building%20agentic%20AI%20workflows). 

Then, include a bullet list of **key features/advantages** of Marvin 3 (5-7 points). For each bullet, use a brief phrase in **bold** followed by a colon and an explanation:
- **Task-Centric Design**: break complex problems into discrete tasks that are easy to manage [oai_citation_attribution:77‡github.com](https://github.com/PrefectHQ/marvin#:~:text=%2A%20Task,AI%20agents%20within%20a%20single).
- **Specialized AI Agents**: create agents with specific roles or personalities for different tasks [oai_citation_attribution:78‡github.com](https://github.com/PrefectHQ/marvin#:~:text=Agents%20are%3A).
- **Type-Safe Outputs**: enforce structured results using Pydantic models, so outputs integrate easily with code [oai_citation_attribution:79‡github.com](https://github.com/PrefectHQ/marvin#:~:text=%2A%20Task,AI%20agents%20within%20a%20single).
- **Lightweight & Fast**: minimal overhead to add Marvin to your project – it's just a Python library, no heavy infrastructure.
- **Transparent Workflows**: you retain control and insight into each step (clear logs, no magic black boxes) [oai_citation_attribution:80‡github.com](https://github.com/PrefectHQ/marvin#:~:text=Marvin%20is%20a%20Python%20framework,for%20building%20agentic%20AI%20workflows).
- **Multi-Agent Orchestration**: coordinate multiple LLMs collaboratively when needed (teams and swarms of agents).
- **Developer-Friendly**: straightforward API that "just works", so you can focus on your application logic (Marvin handles the prompt engineering details).

After the bullet list, include a short "quick look" code snippet to illustrate Marvin’s simplicity. For example:
\`\`\`python
import marvin
result = marvin.run("Write a short poem about artificial intelligence")
print(result)
\`\`\`
Then, show an example output as a quote block (a few lines of a poem). Preface this example with a sentence like: "With Marvin, getting an AI-generated result can be as simple as one line of code:".

Finally, conclude the page with a sentence encouraging the reader to continue to the Quickstart to begin using Marvin (e.g., "Next, let's get Marvin set up and run our first task!").

Use a warm, encouraging tone throughout. Assume the reader may be new to LLM tools, so avoid unexplained jargon. Keep paragraphs short and crisp. 

Introduction – Installation & Setup

Summary: This page provides instructions to install Marvin and verify that it’s working. It should cover installation via pip (and any other method like uv mentioned) ￼, and then configuration of API keys or credentials needed to use LLM providers (Marvin’s default is OpenAI, so explain setting OPENAI_API_KEY) ￼. If Marvin requires Python 3.9+ or any environment prerequisites, mention those. Possibly note that Marvin is lightweight with few dependencies, and that installing will pull in necessary Pydantic AI and providers for OpenAI default. After installation, instruct how to do a quick sanity test (maybe running marvin.run("Hello") in a Python shell to ensure it returns something). This page should be straightforward and task-focused, likely using a numbered list for steps (1. Install, 2. Set API key, 3. Verify). Ensure it’s accessible to beginners (explain how to set environment variables on different OS, e.g., export on Mac/Linux, or set in .env on Windows). Also mention where to find more info on provider setup (if using Azure or others, possibly linking to the Model Providers page or Pydantic AI docs). The content should be concise and clear, avoiding any unnecessary info.

Prompt:

Draft the **"Installation & Setup"** page for Marvin 3 documentation. The goal is to help users get Marvin installed and configured quickly.

Start with a brief sentence on Marvin’s Python package availability (e.g., "Marvin is available as a Python package on PyPI, making installation quick and easy."). Then present a step-by-step guide:

1. **Install the Marvin package** – Provide the `pip install marvin` command [oai_citation_attribution:83‡github.com](https://github.com/PrefectHQ/marvin#:~:text=,marvin). Mention Python version requirements if any. Also note alternative install methods if relevant (like using `uv` tool as shown [oai_citation_attribution:84‡github.com](https://github.com/PrefectHQ/marvin#:~:text=,marvin), but pip is primary). For example:
   \`\`\`bash
   pip install marvin
   \`\`\`
   (If Marvin requires any additional installation for specific features, mention that briefly, but likely not at this stage.)

2. **Configure LLM provider credentials** – Explain that by default Marvin uses OpenAI’s API. Instruct setting the `OPENAI_API_KEY` environment variable [oai_citation_attribution:85‡github.com](https://github.com/PrefectHQ/marvin#:~:text=Configure%20your%20LLM%20provider%20,supports%20all%20Pydantic%20AI%20models) so Marvin can access the OpenAI model. Show an example for Unix-like systems:
   \`\`\`bash
   export OPENAI_API_KEY="your-openai-key"
   \`\`\`
   and note Windows equivalent (set command or using an .env file). Mention that Marvin supports other providers too; for now, ensure OpenAI is set so the quickstart works. Possibly hint: "You can find more on using other models in the Configuration section."

3. **Verify the installation** – Suggest running a short Python snippet to confirm everything is set. For example:
   \`\`\`python
   import marvin
   print(marvin.run("Hello, Marvin!"))
   \`\`\`
   Explain that if Marvin is installed and the API key is correct, this should return a friendly AI-generated greeting. If any issues occur (like missing API key), Marvin will raise an error – mention common pitfalls (no API key, internet access required, etc.) and how to fix them.

Keep the tone helpful and straightforward. Use simple language and assume the reader might be relatively new to Python. Use bullet points or numbered steps as above to make it scannable. Also, reassure the user that Marvin has minimal setup: once the API key is in place, they’re ready to start building with Marvin.

Introduction – Quickstart

Summary: The Quickstart page should get the user to run a simple Marvin example end-to-end within minutes. It will build on the installation, assuming Marvin is installed and API key set. Provide a short Python script or interactive session that demonstrates a basic use of Marvin – for example, using marvin.run to perform a simple task and printing the result. This could be similar to ControlFlow’s quickstart example of writing a poem ￼. We want to illustrate Marvin’s one-liner usage (maybe generating text) and possibly a slightly more involved example with a specified output type or using marvin.summarize to show a utility function. The Quickstart should not yet dive into threads or multiple tasks – keep it simple and satisfying, like “you’ve successfully gotten output from the AI!”. The page should explain what’s happening in the code in comments or text (e.g., “This creates a task, runs it with an AI agent, and returns the result” similar to controlflow’s explanation ￼). Possibly include a second example to hint at structured output, e.g., marvin.run("2+2", result_type=int) to show it returns 4. By the end, the user should feel confident that Marvin is working and have a taste of its capabilities. Encourage them to explore further in subsequent sections.

Prompt:

Generate the **"Quickstart"** documentation page for Marvin 3. This page should quickly demonstrate Marvin’s basic usage with minimal code, so the user sees something working right away.

Begin with a short introduction sentence, e.g., "Now that Marvin is installed, let's run our first AI task!" then proceed to a simple example.

Provide a code example in a Markdown code block. The example should be fully self-contained and short:
- Import Marvin (e.g., `import marvin`).
- Use `marvin.run` with a straightforward prompt, such as asking for a poem or a joke (something fun but short).
- Print the result.

For instance:
\`\`\`python
import marvin

# Ask Marvin (the AI) to do something simple
result = marvin.run("Write a one-sentence description of Marvin.")
print(result)
\`\`\`
After the code, show an example **output** (maybe as a block quote or commented) so the user knows what to expect. For example:
*Output:* "Marvin is an AI toolkit that helps you build smart applications easily."

Next, explain briefly what happened: "In this quickstart example, we called `marvin.run` with a prompt. Under the hood, Marvin created a task, assigned it to an AI agent (using the default GPT-4 model), and immediately executed it [oai_citation_attribution:88‡controlflow.ai](https://controlflow.ai/welcome#:~:text=The%20,10%2C%20and%20flows). The result is returned as a Python string, which we printed out."

Optionally, include one more short example to showcase another simple capability – for example, using `marvin.summarize`:
\`\`\`python
text = "Large language models are amazing but can be hard to integrate."
summary = marvin.summarize(text)
print(summary)
\`\`\`
Output (example): "LLMs are powerful, but integrating them can be challenging."

Explain in one sentence: "`marvin.summarize` is a convenience function for quickly summarizing text."

Keep explanations concise and focused on showing that Marvin works and is easy to use. Use an encouraging tone, and perhaps end with: "That’s it! In just a couple of lines, you’ve used Marvin to get AI-generated content. In the next sections, we’ll dive deeper into how Marvin works and what else you can do." 

Ensure the formatting is clean: code blocks for code, brief comments inside code if needed, and minimal text explaining each step.

Introduction – Tutorial: Building a Multi-step Workflow

Summary: This tutorial page is a guided, hands-on example that demonstrates Marvin’s capabilities in a realistic scenario. It should walk the user through building a small application or solving a problem with multiple steps, showcasing threads, tasks, and agents together. A great candidate (based on the Marvin 3 workflow example ￼ ￼) is a tutorial to create a simple “AI writer” that asks the user for a topic, researches it, and produces a structured article. The tutorial would be structured into sections: 1) Goal – explain what you’ll build (e.g., an AI that writes a short article given a topic), 2) Step 1: Getting user input – show using marvin.run with cli=True or just input() to get a topic ￼, 3) Step 2: Researching – a Marvin task to gather key points on the topic ￼, 4) Step 3: Writing – use a specialized Agent (writer) and a task to compose the article with the research info ￼. Show how all steps are done within a marvin.Thread() to preserve context ￼. Provide code snippets for each part and the final output assembly. Throughout, explain what each step is doing and how Marvin is enabling it (e.g., context from research is passed into the writing task). Include the final printed result (maybe abbreviated) to show success. The tone should be tutorial-like and encouraging, ensuring the user can follow along. This page will cement understanding by example and tie together multiple Marvin features.

Prompt:

Write a step-by-step **tutorial** for Marvin 3 titled "Building a Multi-step AI Workflow." 

Introduce the tutorial with a few sentences describing the end goal: for example, "In this tutorial, we'll build a simple AI-powered article writer. Marvin will guide us through asking the user for a topic, researching it, and then writing a short article about it – all in an automated workflow."

Break the tutorial into clear steps with subheadings. For example:

**Step 1: Start a Marvin Thread for context** – Explain that we'll use a `marvin.Thread` to maintain context between steps (so the AI remembers what happened in previous tasks). Provide a code snippet:
\`\`\`python
import marvin
from marvin import Thread

# Start a thread to maintain context across multiple tasks
with Thread() as thread:
    # (we will fill in tasks here)
\`\`\`
Explain that any tasks inside this `with` block will share conversation history and state.

**Step 2: Get the topic from the user** – Use Marvin to interactively get input. For simplicity, you can either use Python's `input()` or Marvin's `cli=True` feature. The Marvin example uses `marvin.run("Ask the user for a topic...", cli=True)` [oai_citation_attribution:95‡pypi.org](https://pypi.org/project/marvin/3.0.0/#:~:text=,cli%3DTrue). Show that:
\`\`\`python
    topic = marvin.run("Ask the user for a topic to write about.", cli=True)
\`\`\`
Tell the reader that running this will prompt them in the console to input a topic, and Marvin will capture it. After this line, we have a topic to work with.

**Step 3: Research the topic** – Now use Marvin to gather some information. For example:
\`\`\`python
    research = marvin.run(f"Research key points about {topic}", result_type=list[str])
\`\`\`
Explain that here we call Marvin to "research" the topic and we expect a list of strings as the result (key points) by setting `result_type=list[str]`. Marvin will then return a Python list of key point strings about the topic.

**Step 4: Write the article** – Create a specialized agent (e.g., a writing assistant) to compose the article. First, show how to make an Agent:
\`\`\`python
    writer = marvin.Agent(
        name="Writer",
        instructions="Write clear, engaging content for a technical audience."
    )
\`\`\`
Explain in text: "We create a `Writer` agent with instructions on style and audience. This agent will be used to ensure the article has a consistent tone."

Now use this agent to write the article using the research:
\`\`\`python
    article = marvin.run(
        "Write an article on the topic using the research provided.",
        agent=writer,
        result_type=dict
        context={"research": research}
    )
\`\`\`
(To keep it simple, you might use `result_type=dict` with keys for title, content, etc., or just expect a string. The Marvin example used a Pydantic BaseModel Article with title, content, key_points. If that's too complex, simplify to expecting a dict with 'title' and 'content'.)

Explain each parameter: `agent=writer` tells Marvin to use our specialized writer agent for this task; `context={"research": research}` provides the information we gathered to the prompt so the agent can use it; `result_type=dict` (or a BaseModel if advanced) ensures the output is structured (like a dictionary with keys "title" and "content").

**Step 5: Output the result** – After exiting the thread (the with block), print the article's title and content:
\`\`\`python
# outside the thread context
print(f"# {article['title']}\\n\\n{article['content']}")
\`\`\`
(Adapt if using a BaseModel, e.g., `article.title`).

Now, in the tutorial text, mention what to expect: Marvin will have a conversation with you to get a topic, do research silently (you might see some console logs of it thinking), and then produce an article draft. The final print will display an article title and content.

Conclude the tutorial with a short note: "We just built a mini autonomous workflow with Marvin – it accepted input, did multi-step reasoning, and generated a structured result. From here, you can tweak the agent instructions or add more steps (like an editing agent) to further improve the output. This example demonstrates how Marvin makes it straightforward to orchestrate complex tasks with minimal code."

Ensure the writing is clear and each step is explained so a user can follow along and understand why we do each part. Use second person ("you") to guide the user. Keep code blocks separate and properly indented for the with block context.

Core Concepts – Tasks

Summary: The Tasks page details what tasks are in Marvin and how to use them. It should start by defining a Task conceptually: a self-contained objective for the AI to accomplish, which produces a result. Explain that calling marvin.run("prompt") implicitly creates and runs a Task, and that you can also explicitly create a marvin.Task(...) object for more control. Highlight that tasks have important properties: instructions (the prompt or goal), result_type (to specify the expected output type), optional tools and context. Mention that tasks are executed by agents (default agent if none specified). Use examples to illustrate usage: a simple task (via marvin.run), then an explicit Task with custom options (like the one that finds an IP address using a tool ￼). Emphasize each of the four qualities of tasks from the reference: Objective-Focused, Tool-Enabled, Observable, Composable ￼. That can be a nice formatted list or bold terms in the text. Also explain how tasks can be chained (either by planning or by threads), but detailed orchestration will be in Threads page – here just note that tasks can depend on each other’s outputs. The tone should be informative, assuring the reader that tasks are easy to create. Include at least one code snippet of creating a Task manually and running it (task.run()), showing how to retrieve its result. Possibly show how task = marvin.Task(...); result = task.run() compares to marvin.run(...). This page sets the foundation for understanding Marvin’s operation.

Prompt:

Compose the **"Tasks"** concept page for Marvin 3 docs. Aim to explain what tasks are and how to use them effectively.

Begin with a definition: "A *Task* in Marvin represents a single objective or prompt that an AI agent will complete." Explain that tasks are the fundamental unit of work [oai_citation_attribution:98‡github.com](https://github.com/PrefectHQ/marvin#:~:text=Tasks) – every query you give Marvin is a task under the hood.

Next, explain how to create and run tasks:
- The simplest way: using `marvin.run("some instruction")` which creates a task on the fly and runs it [oai_citation_attribution:99‡github.com](https://github.com/PrefectHQ/marvin#:~:text=).
- The more explicit way: using the `marvin.Task` class. Show an example:
  \`\`\`python
  from marvin import Task
  my_task = Task(instructions="Translate 'hello' to Spanish", result_type=str)
  result = my_task.run()
  print(result)  # "hola"
  \`\`\`
  Explain that here we defined a task with certain instructions and an expected result type (string for the translation). When we call `run()`, Marvin executes the task with an AI agent and returns the result.

Discuss **Task properties**:
- **Instructions**: the prompt or description of what we want. This can be a brief command or a detailed request.
- **Result Type**: (optional but powerful) specify a Python type or Pydantic model for the result. Marvin will ensure the output conforms to this type. This yields structured, validated data instead of raw text [oai_citation_attribution:100‡github.com](https://github.com/PrefectHQ/marvin#:~:text=%2A%20Task,AI%20agents%20within%20a%20single).
- **Tools**: (optional) attach custom functions the task is allowed to use to achieve its goal. For example, if a task might need to fetch data or run a command, you can provide a Python function in `tools` [oai_citation_attribution:101‡github.com](https://github.com/PrefectHQ/marvin#:~:text=%2A%20Objective,workflows%20by%20connecting%20tasks%20together). The AI can then decide to call that function. (We will detail tools on a separate page, but give a one-liner example, e.g., a task that uses a `run_shell_command` tool to get system info).
- **Context**: (optional) supply additional context data to the task. This could be any supporting information the AI might need (like previous results, or domain knowledge). Context is provided as a dict of variables the task can use.

Emphasize that tasks are executed by an **Agent** – by default Marvin uses a generic agent (with GPT-4 or specified default model) to run tasks. You can also assign a custom agent to a task (we cover Agents later, but mention you can do `marvin.run(prompt, agent=my_agent)` or `Task(..., agent=my_agent)`).

After explaining the properties, highlight the four key characteristics of tasks in Marvin, perhaps as a bullet list:
- **Objective-Focused** – a task should have one clear goal or question [oai_citation_attribution:102‡github.com](https://github.com/PrefectHQ/marvin#:~:text=Tasks%20are%3A).
- **Tool-Enabled** – tasks can utilize external tools (functions) to enhance their abilities [oai_citation_attribution:103‡github.com](https://github.com/PrefectHQ/marvin#:~:text=%2A%20Objective,workflows%20by%20connecting%20tasks%20together).
- **Observable** – tasks provide insight into their execution (Marvin logs each step, tool usage, etc., so you can observe what's happening) [oai_citation_attribution:104‡pypi.org](https://pypi.org/project/marvin/3.0.0/#:~:text=Tasks%20are%3A).
- **Composable** – you can chain tasks together to form larger workflows [oai_citation_attribution:105‡pypi.org](https://pypi.org/project/marvin/3.0.0/#:~:text=Tasks%20are%3A) (we’ll see how in the Threads and Planning sections).

Include a slightly more complex example to tie this together: e.g., "Using tools in a Task." Provide a code snippet similar to the IP address example:
\`\`\`python
import subprocess
def run_shell_command(cmd: list[str]) -> str:
    "Run a shell command and return its output."
    return subprocess.check_output(cmd).decode()

task = Task(
    instructions="Find the current IP address",
    result_type=str,
    tools=[run_shell_command],
    context={"os": "Linux"}  # just an example context
)
print(task.run())
\`\`\`
Then describe: "In this example, our task is to get the current IP address. We gave the task a Python tool `run_shell_command` that it can use to execute shell commands. Marvin’s agent will decide to use this tool to fulfill the task (as you can see in the console logs, it calls `run_shell_command(['ip', 'addr', 'show'])` or the appropriate command for your OS). The result is returned as a string containing the IP."

Wrap up by reinforcing: **Tasks** are the building blocks in Marvin. They encapsulate a query or action for the AI. In practice, you might not always create Task objects manually – using `marvin.run` is often enough for quick tasks – but understanding Tasks allows you to harness advanced features like tools, context, and structured outputs.

Keep the tone educational and clear. Avoid overly technical language; prioritize explaining concepts in simple terms and using examples to illustrate.

Core Concepts – Agents

Summary: The Agents page describes what an Agent is in Marvin and how it differs from a raw LLM call. Explain that an Agent encapsulates an LLM plus instructions/persona and possibly tools and settings, allowing reuse across tasks ￼ ￼. Highlight that Marvin’s Agent is analogous to an AI assistant with a certain role. Cover how to create an agent (marvin.Agent(name="X", instructions="Y", model=..., tools=[...])) and the main properties: name (for identification/logging), instructions (the role/prompt it always follows), model (optional custom model or provider settings, otherwise uses default GPT-4), tools (tools available to that agent for any task). Emphasize that agents can be saved and reused in many tasks, promoting consistency. Also discuss that multiple agents can collaborate (but detail of teams is another page). Provide examples: a “Technical Writer” agent (like in the example ￼) and using it with marvin.run(prompt, agent=that_agent). Show how an agent can directly run tasks via agent.run("prompt") as shorthand ￼. Then list the key qualities of agents: Specialized (you tailor them for a job), Portable (pass them around to tasks), Collaborative (can form teams), Customizable (model and parameters) ￼. The tone should encourage using agents to manage complexity (e.g., instead of writing one prompt to do everything, you can break into roles). Mention that if no agent is specified, Marvin uses a default one behind scenes. Possibly also note Marvin’s default agent uses OpenAI GPT-4 by default ￼, but this can be changed via configuration or model argument. Include at least one code snippet: creating an agent and using it in a couple of tasks.

Prompt:

Create the **"Agents"** concept page for Marvin 3 documentation. This page should explain what agents are and how to use them.

Start by defining an Agent: "An *Agent* in Marvin represents a configured AI persona or worker that can carry out tasks." Explain that an agent wraps an LLM with a specific role or behavior (through instructions) and settings. It's like a character or expert you can assign tasks to.

Discuss why agents are useful: they let you reuse the same configuration for multiple tasks, ensuring consistent style or knowledge. For example, you might have a "Tech Writer" agent and a "Proofreader" agent for different purposes.

Show how to create an agent using `marvin.Agent`:
\`\`\`python
from marvin import Agent
writer = Agent(
    name="Technical Writer",
    instructions="Write clear, engaging content for developers.",
    model="openai/gpt-4",  # this could be optional, default is GPT-4
)
\`\`\`
Explain each field:
- **name**: just a label (could be anything, often reflecting its role, and appears in logs).
- **instructions**: the persistent prompt that guides the agent’s style or expertise (like a system prompt or role).
- **model**: (optional) specify which LLM to use (if not provided, Marvin uses its default model, e.g., OpenAI GPT-4). This can also accept a model object from Pydantic AI for advanced usage.
- **tools**: (optional) a list of tools (Python functions) the agent can use by default for any task (if you know this agent will often need certain tools, you can attach them here).

After creating an agent, show how to use it:
\`\`\`python
# Using the agent to perform tasks
topic = "how to use Python type hints"
result = writer.run(f"Write a short blog post about {topic}.")
print(result)
\`\`\`
This example should illustrate that we can call `agent.run(prompt)` directly, which is equivalent to `marvin.run(prompt, agent=agent)` – it runs the given prompt with that agent.

Explain that because we gave the agent instructions to write for developers, the output will follow those guidelines on every use. The agent carries its persona across tasks, which is useful for maintaining consistency.

Also mention you can use agents with the `marvin.run` function by passing the agent, or you can attach an agent to a Task as well.

Now list the key benefits (qualities) of Marvin agents (possibly as bullets or bold headers):
- **Specialized**: An agent can be specialized to a task or domain by tuning its instructions (e.g., a friendly customer support agent vs. a precise data analyst) [oai_citation_attribution:112‡github.com](https://github.com/PrefectHQ/marvin#:~:text=Agents%20are%3A).
- **Portable**: Once created, the same Agent can be reused for many tasks in different parts of your program [oai_citation_attribution:113‡github.com](https://github.com/PrefectHQ/marvin#:~:text=,model%2C%20temperature%2C%20and%20other%20settings). This is more efficient than writing the same prompt instructions over and over.
- **Collaborative**: Multiple agents can work together. (Briefly note that Marvin allows you to form teams of agents – which will be discussed later in the Teams page – enabling complex workflows where agents delegate tasks to each other) [oai_citation_attribution:114‡github.com](https://github.com/PrefectHQ/marvin#:~:text=,model%2C%20temperature%2C%20and%20other%20settings).
- **Customizable**: You have full control over the agent’s settings – choose different LLM models, adjust parameters (if supported via the model interface like temperature), and give it tools. This means you can tailor performance vs cost, or capabilities (like using a code-focused model for coding tasks).

Include an example to illustrate customization: e.g., creating an agent with a non-OpenAI model using Pydantic AI:
\`\`\`python
from marvin import Agent
from pydantic_ai.models.anthropic import AnthropicModel

researcher = Agent(
    name="Researcher",
    instructions="Provide thorough, factual answers with references.",
    model=AnthropicModel("anthropic/claude-2", api_key="...")  # using Anthropic via Pydantic AI
)
\`\`\`
You can omit actual keys in the example, just show that it's possible. Explain: "Here we configured an agent to use Claude-2 by Anthropic for a different style of response. Marvin supports many models through Pydantic AI, which we can plug in like this."

End the page by suggesting: "In summary, use Agents to encapsulate different AI behaviors in your application. When a task needs a particular style or domain expertise, assigning it to a matching Agent yields better results and cleaner code."

Maintain an instructive tone, using "you can..." and real-world analogies (like thinking of agents as team members with specific roles). 

Core Concepts – Threads (Workflows)

Summary: This page explains Marvin’s approach to workflows via Threads. Start by clarifying that a Thread is Marvin’s abstraction for a sequence of tasks that share context – essentially a conversation or workflow context (similar to how one might think of a “conversation thread” or how ControlFlow’s Flow worked) ￼. Mention that under the hood, Marvin uses threads to tie tasks together, preserving memory of previous prompts and results. Explain usage: the marvin.Thread context manager. Show a simple example of using with marvin.Thread() as thread: and running multiple marvin.run calls inside it, and how each call has access to the prior ones’ context (no need to manually pass if Marvin automatically includes relevant history, but context can also be passed explicitly if needed). Emphasize that threads allow dependent tasks and sequential logic. Also explain that threads have an identifier option for persistence (so you can resume a thread by id). Include an example scenario: e.g. ask a follow-up question referencing the previous answer, inside a thread. Also mention that threads handle storing the conversation in a database (by default SQLite) ￼, which is why context persists even if you create a thread with an id and reuse it. Possibly cover how this relates to the concept of “memory” – thread is where the memory lives. If applicable, mention differences from Marvin 2/ControlFlow (Flow renamed to Thread). The tone should clarify that threads are optional but powerful: you only use them when you need multi-step continuity; for single calls they aren’t needed. Also mention that all Marvin’s high-level functions (summarize, etc.) automatically attach to a thread if inside one (per the Marvin docs: “All Marvin functions have thread management built-in…” ￼). Encourage usage for building chatbots or multi-step workflows. Provide at least one code snippet demonstrating two related calls within a thread and showing that the second can use info from the first.

Prompt:

Draft the **"Threads (Workflows)"** page for Marvin 3 docs, focusing on how to maintain context across multiple AI calls.

Open with an explanation: "A **Thread** in Marvin is a mechanism to group a series of tasks into a single context or conversation. Threads let tasks share information, so you can build multi-step workflows where each step builds on the last."

Compare it to a conversation: "Think of a thread like a conversation thread with the AI – it's aware of what has been said or done earlier in the thread."

Introduce the usage of `marvin.Thread`:
- Explain that it's used as a context manager (`with marvin.Thread() as thread:`).
- Within the `with` block, any `marvin.run` or Marvin function call automatically logs its interaction to the thread’s history [oai_citation_attribution:118‡github.com](https://github.com/PrefectHQ/marvin#:~:text=Planning%20and%20Orchestration). The next call can access that history, which means the AI has the context of previous tasks.

Provide a basic example:
\`\`\`python
import marvin

with marvin.Thread() as thread:
    answer1 = marvin.run("What is the capital of France?")
    print(answer1)  # e.g., "Paris."

    # Now ask a follow-up question that relies on previous answer
    answer2 = marvin.run("How many people live there?")
    print(answer2)  # uses context that "there" = Paris
\`\`\`
Explain what's happening: The second `marvin.run` didn't explicitly mention "Paris", but because it’s in the same thread, Marvin knows "there" refers to the capital of France from the previous answer. This is context carry-over in action.

Emphasize: **Threads preserve memory.** Marvin automatically includes relevant prior conversation from the thread when formulating prompts for subsequent tasks, so the AI remembers context without you re-supplying it each time.

Mention thread identifiers: "You can give a thread an optional ID (e.g., `with marvin.Thread(id=\"support-chat-123\"):`) [oai_citation_attribution:119‡github.com](https://github.com/PrefectHQ/marvin#:~:text=,decorator%20has%20been%20removed). This is useful if you want to resume or reference the same thread later (for example, a persistent chat session across program runs). Marvin stores thread history in a SQLite database by default [oai_citation_attribution:120‡github.com](https://github.com/PrefectHQ/marvin#:~:text=,to%20reset%20data%20during%20updates), so if you use the same id again, it can retrieve past context."

Discuss how threads relate to **workflow orchestration**: For more complex flows, you might manually chain tasks inside a thread (like first do A, then use result in B). Provide a slightly more advanced example (without going into full planning, just manual orchestration):
\`\`\`python
with marvin.Thread() as thread:
    data = marvin.run("Fetch data on climate trends for 2020s.", result_type=list[str])
    analysis = marvin.run("Analyze the following data: {data}", context={"data": data})
\`\`\`
Explain: "In this thread, the second run explicitly uses the result of the first by injecting it via context. We could also rely on implicit memory, but using the `context` parameter ensures the data is passed clearly."

Note: All top-level Marvin APIs (summarize, classify, etc.) will also utilize the thread if called within one – meaning you can mix and match those calls inside the `with Thread:` and they all share the same memory [oai_citation_attribution:121‡github.com](https://github.com/PrefectHQ/marvin#:~:text=All%20Marvin%20functions%20have%20thread,that%20share%20context%20and%20history).

Add a section on **When to use Threads**:
- If your interaction with the AI is one-off and stateless, you don't need a thread (Marvin creates a temporary thread internally anyway).
- If you want a continuous conversation or a multi-step process (like an agent planning steps or a Q&A session), wrap it in a Thread.
- In chatbot or assistant applications, you'll likely maintain one thread per user session, so the assistant has a memory of the conversation.

Finally, clarify the difference between threads and flows (for those coming from ControlFlow): "In Marvin 3, Threads replace the Flow concept from ControlFlow [oai_citation_attribution:122‡github.com](https://github.com/PrefectHQ/marvin#:~:text=,decorator%20has%20been%20removed). They function similarly as context managers for workflows, but there's no separate decorator needed – you simply use the Thread context."

Close by reinforcing that threads give you **context continuity** and are a cornerstone for building complex workflows with Marvin. The user should feel that using threads is straightforward (just a with-block) and yields powerful results in terms of AI remembering previous steps.

Keep sentences clear and the example outputs brief. Ensure the examples demonstrate the concept clearly.

Core Concepts – Tools and Context

Summary: This page digs into providing external tools and context to Marvin tasks, allowing the AI to do more than it could with just its model knowledge. Start by defining a “tool” in Marvin: a Python function that an agent can call during task execution to perform some action (like API call, calculation, file access) ￼. Explain that tools extend Marvin’s abilities beyond the base LLM – similar to giving the AI a calculator or internet access, but in a controlled way. Then explain how to use tools: by passing them into a task or agent (tasks via tools=[func] parameter ￼, or globally to an agent via agent’s tools list ￼). Provide a simple example (like the dice roll example from ControlFlow ￼ or the shell command example from Marvin’s docs ￼ ￼). Walk through that example: the agent sees the function’s name and docstring and can decide to call it with certain arguments to get a result it needs. Mention that Marvin automatically infers how to call the tool from its signature and docstring (thanks to Pydantic’s introspection, possibly) ￼. Also emphasize context: context is static info you provide to the task/agent that it can use when responding (but context isn’t an executable function, just data). For example, giving a task a context={"user_profile": {...}} so it has user info to personalize the answer. Show how context keys can be referenced in prompt (Marvin likely auto-injects it or the prompt template uses it). Possibly mention that Marvin’s prompt format might incorporate context keys (like the example marvin.run("... {data}", context={"data": X})). Provide best practices for using tools: keep them simple, use clear docstrings with usage instructions, and provide type hints ￼ ￼. Also caution that giving too many powerful tools can be risky – highlight that you control what the AI can do. The tone should excite developers about integrating their own code with AI easily, one of Marvin’s strengths. End with encouraging readers to experiment by giving Marvin small utility tools from their codebase to make it more powerful.

Prompt:

Write the **"Tools and Context"** page for Marvin 3 documentation. This page explains how to extend Marvin's capabilities by giving it access to custom tools (functions) and additional context data.

Begin by explaining **what tools are** in this context: "Tools are simply Python functions that you allow Marvin’s agents to call during a task. They let the AI interact with the outside world or perform specific computations beyond the LLM’s native capabilities [oai_citation_attribution:132‡controlflow.ai](https://controlflow.ai/patterns/tools#:~:text=Give%20agents%20new%20abilities%20with,custom%20tools)."

Make it concrete with an example scenario: "For instance, you might provide a `search_web()` tool that lets the AI retrieve live information, or a `calculate()` tool for math. Marvin’s agent can decide to use these tools when appropriate to fulfill the task."

Explain **how to add a tool to a task**: via the `tools` parameter. Show a basic example:
\`\`\`python
import random
def roll_die() -> int:
    "Roll a six-sided die and return the result."
    return random.randint(1, 6)

result = marvin.run("Roll a die twice and add the results", tools=[roll_die])
\`\`\`
Describe what happens: Marvin's agent sees it has a tool `roll_die` available (with the docstring "Roll a six-sided die..."). So, to answer the prompt, it might call `roll_die` twice internally and then add them up in its reasoning, finally returning the sum as the result [oai_citation_attribution:133‡controlflow.ai](https://controlflow.ai/patterns/tools#:~:text=def%20roll_die%28%29%20,sided%20diee.%22%22%22%20return%20random.randint%281%2C%206). The user just gets the final answer (e.g., "The dice rolls are 3 and 5, totaling 8.").

Next, explain **how tools are presented to the agent**: Marvin uses the function name, signature, and docstring to inform the AI of what the tool does and how to call it [oai_citation_attribution:134‡controlflow.ai](https://controlflow.ai/patterns/tools#:~:text=Clear%20name%20and%20description). This is why writing a clear docstring is important. Mention that type hints on parameters and return values help Marvin format the calls correctly [oai_citation_attribution:135‡controlflow.ai](https://controlflow.ai/patterns/tools#:~:text=Type%20hints) (the AI will know what type of input to give and what output to expect).

Then, cover **attaching tools to an Agent**: If you have an agent that should always have certain tools, you can give it a `tools=[...]` list when creating it [oai_citation_attribution:136‡github.com](https://github.com/PrefectHQ/marvin#:~:text=api_key%3Dos.getenv%28,tools%3D%5Bwrite_file%5D%2C). Then any task run by that agent can use those tools. For example:
\`\`\`python
assistant = marvin.Agent(name="Calculator", instructions="You can do math", tools=[math.sqrt])
answer = assistant.run("What is the square root of 16?")
\`\`\`
The agent "Calculator" always has `math.sqrt` available, so it will use that for computing the answer.

Now talk about **context**: "Context is information you pass into a task that the AI can use to better perform its job." Unlike tools, context isn't an action, it's data. For example, if the task is "Recommend a book for the user," you might pass context like `{"favorite_genres": ["sci-fi", "mystery"]}` so the AI knows the user's preferences.

Show how to use context in a call:
\`\`\`python
user_profile = {"name": "Alex", "interests": ["cycling", "machine learning"]}
prompt = "Draft a personalized greeting for {name}, who is interested in {interests[1]}."
message = marvin.run(prompt, context=user_profile)
\`\`\`
Explain that Marvin will fill in the placeholders or at least have that info while generating the message. (Even if Marvin doesn’t do string interpolation automatically, its prompt would include the context details in some form.)

Best practices section:
- **Keep tools focused**: Each tool should do one thing well (like a single responsibility). Complex multi-step processes can often be broken into multiple tools or tasks.
- **Use clear naming and docstrings**: The tool’s name and docstring should make its purpose obvious to the AI [oai_citation_attribution:137‡controlflow.ai](https://controlflow.ai/patterns/tools#:~:text=Clear%20name%20and%20description). For example, `def lookup_stock_price(ticker: str) -> float:` with a docstring "Look up the current stock price for the given ticker symbol." The agent will then know exactly when and how to use it.
- **Type hints**: Always add type hints for parameters and return types [oai_citation_attribution:138‡controlflow.ai](https://controlflow.ai/patterns/tools#:~:text=Type%20hints). Marvin uses these to enforce the correct usage and to validate outputs, making interactions more robust.
- **Security & Control**: Remember that the AI decides when to use a tool. Only provide tools you're comfortable the AI using. Avoid tools that could perform destructive actions unless absolutely necessary, and even then handle outputs carefully (Marvin does not have a notion of tool permission beyond what you give it).
- **Testing**: Try out tasks with your tools to see how the AI uses them. Marvin will log tool usage during a run (you'll see something like "Tool: tool_name Input: {...} Output: {...}" in the output [oai_citation_attribution:139‡pypi.org](https://pypi.org/project/marvin/3.0.0/#:~:text=%E2%95%AD%E2%94%80%20Agent%20,%E2%94%82%20%E2%95%B0%E2%94%80%E2%94%80%E2%94%80%E2%94%80%E2%94%80%E2%94%80%E2%94%80%E2%94%80%E2%94%80%E2%94%80%E2%94%80%E2%94%80%E2%94%80%E2%94%80%E2%94%80%E2%94%80%E2%94%80%E2%94%80%E2%94%80%E2%94%80%E2%94%80%E2%94%80%E2%94%80%E2%94%80%E2%94%80%E2%94%80%E2%94%80%E2%94%80%E2%94%80%E2%94%80%E2%94%80%E2%94%80%E2%94%80%E2%94%80%E2%94%80%E2%94%80%E2%94%80%E2%94%80%E2%94%80%E2%94%80%E2%94%80%E2%94%80%E2%94%80%E2%94%80%E2%94%80%E2%94%80%E2%94%80%E2%94%80%E2%94%80%E2%94%80%E2%94%80%E2%94%80%E2%94%80%E2%94%80%E2%94%80%E2%94%80%E2%94%80%E2%94%80%E2%94%80%E2%95%AF)) which helps in debugging if the AI misuses a tool or if the tool returns unexpected results.

Finally, encourage: "Tools and context allow you to integrate Marvin deeply with your own software. By giving the AI functions to call and data to use, you can make it far more powerful and useful, all while keeping you in control of what it can do."

Keep the explanation friendly and use analogies if helpful (e.g., "You can think of tools as 'apps' on a smartphone that the AI can choose to open to get something done"). Ensure clarity on the difference between context and tools. 

Core Concepts – Memory

Summary: The Memory page should clarify how Marvin remembers information over time and how users can manage that memory. Explain that Marvin’s memory refers to the conversation or task history stored in threads (and internally via a marvin.Memory mechanism). Note that by default, Marvin 3 logs all prompts and responses in a local SQLite database ￼, which acts as persistent memory. Outline the benefits: continuity between calls (as seen in Threads), ability to recover context after a crash by reloading a thread with an id. Explain how Memory can be configured: e.g., using MARVIN_DATABASE_URL to set where memory is stored (in-memory or file) ￼, and that currently Marvin uses a simple approach with no vector store unless extended (if that’s the case). If Marvin has a marvin.Memory class or functions (the upgrade notes list marvin.Memory for ControlFlow users ￼, possibly as an object to manage memory), mention how one might explicitly use it (maybe not needed often if threads handle it automatically). Also cover how to limit memory usage: e.g., if conversation gets too long, does Marvin summarize or drop old messages? This might not be implemented yet, but could mention best practices like manually summarizing or truncating if needed. The page might also explain that each agent by default has no long-term memory beyond the thread context (unless you implement something custom). Provide an example of retrieving memory if possible (maybe Marvin API to fetch past messages from a thread). If available, mention how to clear memory (like starting a fresh thread or using the in-memory mode for stateless operation). The tone should reassure that Marvin’s memory is transparent and user-controlled (no hidden state beyond what’s in the thread logs). Encourage understanding that memory persistence is for convenience, and if it’s not desired, how to disable or reset it. Possibly include a short code snippet to show using an existing thread id to resume context.

Prompt:

Write the **"Memory"** page for Marvin 3, focusing on how Marvin retains and manages conversational context.

Start by explaining what "memory" means in Marvin: "Memory refers to Marvin’s ability to remember previous interactions so that context carries over to future tasks." Clarify that this isn't about long-term learning, but session memory (conversation history).

Explain that memory in Marvin is tied to **Threads**. When you use a Thread, all prompts and responses in that thread are stored. Marvin 3 persists this memory automatically: by default, it uses a SQLite database to save conversation history [oai_citation_attribution:143‡github.com](https://github.com/PrefectHQ/marvin#:~:text=,to%20reset%20data%20during%20updates). This means if you create a thread with an id (like "support-session-1") and the program restarts, you can create a new Thread with the same id and Marvin will recall the past conversation.

Give a simple example of persistent memory:
\`\`\`python
# First run
with marvin.Thread(id="demo") as thread:
    marvin.run("Remember this number: 42.")

# Later or in another script
with marvin.Thread(id="demo") as thread:
    result = marvin.run("What number did I ask you to remember?")
    print(result)  # should recall "42" if memory persisted
\`\`\`
Explain: In the first part, Marvin got the instruction to remember 42 (maybe it doesn't output anything or acknowledges). In the second part, because we reused thread id "demo", Marvin has the context that "42" was mentioned, so it can answer accordingly. (This example assumes Marvin actually stores all messages; if not, adjust explanation accordingly.)

Discuss **Memory configuration**:
- The environment variable `MARVIN_DATABASE_URL` controls where memory is stored [oai_citation_attribution:144‡github.com](https://github.com/PrefectHQ/marvin#:~:text=,to%20reset%20data%20during%20updates). By default it might be something like `marvin.db` (SQLite file). If you set it to ":memory:", Marvin will not persist (use in-memory only) [oai_citation_attribution:145‡github.com](https://github.com/PrefectHQ/marvin#:~:text=,to%20reset%20data%20during%20updates) – useful for tests or if you don't want disk writes.
- Currently, Marvin doesn't have a fancy vector-store memory or long-term summarization (assuming that from "no migrations available" note). It's straightforward logging of conversation. So mention: "Marvin’s memory is currently simple but robust: it stores complete message history. In future versions, this may evolve to support more complex memory systems."

If Marvin has a `marvin.Memory` object, explain it briefly: e.g., "For advanced usage, Marvin provides a Memory interface. In most cases, you won't interact with it directly – it's managed when you use Threads. But ControlFlow users might recall a memory provider concept; Marvin 3 uses a default SQLite-backed memory."

Tips or common tasks:
- **Clearing memory**: Start a new thread without an id (or a fresh id) if you want a clean slate. Or set `MARVIN_DATABASE_URL=":memory:"` for ephemeral memory that resets each run.
- **Memory limits**: If you have extremely long threads, be mindful that sending a very large history to the LLM can hit context length limits. At the moment, Marvin does not automatically truncate or summarize old messages. It could be up to you to manage extremely long conversations (for example, manually summarize earlier parts if needed).
- **Privacy**: All memory is stored locally (unless you configure a remote database explicitly). So your data isn't sent anywhere except to the LLM provider when context is included in a prompt.

Provide an example of examining memory (if possible): For instance, maybe mention that if you look at `marvin.settings` or some log, you could see the messages. (If there's an API like `thread.history` or similar, mention it; if not, skip direct retrieval.)

Conclude with reassurance: "Memory is what makes multi-turn interactions with Marvin possible. You have control over it via thread scoping and configuration. By leveraging memory, you can build stateful applications (like chatbots that remember what was said) with ease."

Keep the tone explanatory. Even if some of this is technical, try to keep it approachable (like explaining the idea of conversation history). Use short paragraphs or bullets for config points.

Core Concepts – AI Functions

Summary: This page covers the @marvin.fn decorator and related functionality, which allow users to create “AI functions” easily. Explain that Marvin can turn a normal Python function signature and docstring into an AI-powered implementation ￼. Essentially, when you decorate a function with @marvin.fn, calling that function will invoke an LLM to produce the result, using the function’s name, docstring, and type hints as context. Outline step-by-step how to create one: write a function with no body (or just … pass), add the decorator. For example, a function to answer questions or transform data. Provide a code snippet of a simple AI function definition (like a translate or summarize function as earlier). Show how calling it returns an answer. This is somewhat meta (writing functions that aren’t implemented by code but by AI), so explain the benefits: It’s quick to define custom LLM tasks without crafting prompts every time – the function’s metadata is used to generate the prompt automatically ￼. Also mention that type hints are used to validate output (Marvin will try to conform output to the declared return type) ￼. Possibly reference that this pattern is similar to libraries like DSPy or AI function concepts, but Marvin makes it very simple. Include guidance: ensure docstring clearly states what to do, maybe examples in docstring can help (if supported). Also caution: since the implementation is AI, test these functions to ensure they behave as expected. The tone is empowering – this feature can drastically reduce boilerplate when integrating LLM logic. Maybe provide two examples: one simple (like a math word problem solver function with int output) and one with a Pydantic model output to show complexity. Keep it focused though. End by linking this concept to tasks: an AI function is basically a wrapper that creates a task behind scenes, so it has all benefits of tasks (context, thread integration, etc. – possibly mention that if called inside a thread, they also share context).

Prompt:

Generate the **"AI Functions"** page for Marvin 3 documentation, describing how to use the `@marvin.fn` decorator to create AI-powered functions.

Start by introducing the concept: "Marvin allows you to define Python functions that are implemented by AI under the hood. With the `@marvin.fn` decorator, you declare what the function should do (via its name, parameters, and docstring), and Marvin will handle the rest – using an LLM to provide the output."

Explain **why use AI functions**:
- They let you encapsulate AI prompts as reusable functions. 
- You don't have to manually call `marvin.run` with a prompt every time; you just call your function as if it were implemented normally, which makes code more readable and maintainable.
- They ensure inputs and outputs are structured as specified (type hints enforce that).

Outline how to create one:
1. Write a function signature for what you want the AI to do, including type-annotated parameters and a return type.
2. Write a docstring describing the task clearly (this will guide the AI).
3. Decorate the function with `@marvin.fn`.
4. Do not provide a normal implementation (or you can put `...` or a simple `pass` inside).

Give a concrete example:
\`\`\`python
from marvin import fn

@fn
def summarize_article(article_text: str) -> str:
    """Provide a concise summary of the given article text."""
    # (Marvin will implement this function using AI)
    ...
\`\`\`
Now, in usage:
\`\`\`python
long_text = "OpenAI has introduced a new API for ..."
summary = summarize_article(long_text)
print(summary)  # prints the AI-generated summary
\`\`\`
Explain that when `summarize_article` is called, Marvin intercepts the call. It sees the function name and docstring ("Provide a concise summary...") and uses them to prompt the LLM with the `article_text` argument, aiming to produce a string (as specified by return type) [oai_citation_attribution:149‡twosigma.com](https://www.twosigma.com/articles/a-guide-to-large-language-model-abstractions/#:~:text=Marvin%20has%20more%20recently%20streamlined,an%20output%20from%20the%20LM).

Point out that type hints matter: Marvin will try to make the output a `str` in this case. If you put a more complex type (like a Pydantic model or a list), Marvin will format the output accordingly.

Provide another example, maybe something that returns a structured result:
\`\`\`python
from pydantic import BaseModel

class WeatherInfo(BaseModel):
    temperature: float
    conditions: str

@fn
def get_weather_report(location: str) -> WeatherInfo:
    """
    Get the current weather for the given location.
    Return the temperature in Celsius and general conditions.
    """
    ...
\`\`\`
Now calling:
\`\`\`python
report = get_weather_report("London")
print(report)
# WeatherInfo(temperature=15.2, conditions='Partly cloudy')
\`\`\`
Explain: The AI will generate text that looks like a JSON or Python dict matching WeatherInfo, Marvin will parse it into the `WeatherInfo` model. Under the hood, Marvin likely uses Pydantic to validate that output [oai_citation_attribution:150‡twosigma.com](https://www.twosigma.com/articles/a-guide-to-large-language-model-abstractions/#:~:text=Marvin%20has%20more%20recently%20streamlined,an%20output%20from%20the%20LM). If the AI returns something that doesn't fit, it will error or try to correct.

Mention any limitations or best practices:
- Keep the function’s purpose simple and clearly stated. The AI needs to understand what you want from the docstring.
- If a function is complex, break it into smaller AI functions or use tasks directly.
- Always test the AI function to ensure it's giving reasonable results for typical inputs.
- If needed, you can add examples in the docstring (some frameworks do that to guide the AI; not sure if Marvin uses that, but it could help).
- Remember that at runtime it’s making API calls to the LLM, so handle errors or response times accordingly (you might want retries or timeouts for critical functions, though Marvin or Pydantic AI might handle some of that automatically).

Also highlight that these functions seamlessly integrate with Marvin’s threading and memory. For example, if you call an AI function inside a Thread, it participates in the thread’s context like any other task (so it can use previous info if relevant).

Conclude: "AI functions let you treat AI capabilities as first-class functions in your code, making your codebase cleaner and more intuitive. Instead of writing verbose prompt handling logic, you define what you want, and Marvin takes care of prompting the LLM and parsing the result."

Keep the tone enthusiastic (this is a cool feature) but also clear on what the developer needs to do (provide docstring, etc.). 

Core Concepts – Multi-Agent Teams

Summary: This page focuses on Marvin’s ability to have multiple agents collaborate on tasks via Teams and Swarms. Define a Team as a group of agents working together, possibly with a controlled delegation structure ￼. Define a Swarm as a special kind of Team where all agents can freely collaborate (essentially all-to-all delegation) ￼. Explain scenarios: e.g., a team with a Writer, Editor, and FactChecker agent to collectively produce a result (like the earlier example ￼). Describe how to create a team (maybe Marvin has marvin.Team([...]) or just using Swarm for default behavior). From the release notes, it looks like marvin.Swarm([...]) is provided for the open collaboration case ￼ ￼. Show an example: make a couple of agents and combine them in a swarm, then do swarm.run("prompt") ￼ ￼. Explain what happens: all the agents in the swarm can contribute or propose answers, and the final result is produced (likely through some voting or just one of them answering - clarify if possible; if not, say they all attempt and the swarm yields a combined answer or one of them does). If Teams have a different interface (like maybe specify which agent leads or how delegation happens), mention that conceptually but keep it simple. Possibly mention that under the hood, the “Tool use” concept is extended to agent delegation (i.e., agents can call other agents as tools?). This is advanced, so keep details light. Emphasize the benefit: multi-agent setups allow complex problem solving by splitting roles (like an “ensemble” of specialists). Also reassure that if you don’t need it, you can ignore it, but it’s there for advanced usage. The tone should be explanatory and a bit exploratory, since multi-agent systems are more complex. Use a short example to illustrate collaboration (maybe ask a swarm of a few personas to each give part of an answer). Also caution about complexity: more agents can mean more tokens and cost, so use when appropriate. End with linking back: if someone had used ControlFlow’s multi-agent, this is how Marvin does it now.

Prompt:

Write the **"Multi-Agent Teams"** page for Marvin 3 documentation, explaining how to use multiple agents together (Teams and Swarms).

Start by motivating the feature: "Sometimes a single AI agent isn't enough. You might want one agent to generate ideas, another to critique or fact-check, and another to compile the final answer. Marvin allows multiple agents to collaborate through Teams."

Define **Team**: "A Team is a collection of agents that can work together on tasks [oai_citation_attribution:158‡github.com](https://github.com/PrefectHQ/marvin#:~:text=swarm). You decide how the collaboration works – for example, you could have a leader agent that delegates subtasks to other agents, or a round-robin of contributions. Marvin’s simplest form of team collaboration is the **Swarm**."

Explain **Swarm**: "A Swarm is a type of Team where all agents can freely cooperate and delegate to each other at any time [oai_citation_attribution:159‡github.com](https://github.com/PrefectHQ/marvin#:~:text=swarm). In other words, it's an open collaboration: any agent in the swarm can decide to take action or ask another for help."

Show how to create a swarm:
\`\`\`python
from marvin import Agent, Swarm

# Define individual agents
agent_a = Agent(name="Agent A", instructions="Be concise.")
agent_b = Agent(name="Agent B", instructions="Be verbose and explanatory.")
agent_c = Agent(name="Agent C", instructions="Critique answers and improve them.")

# Create a swarm of these agents
team = Swarm([agent_a, agent_b, agent_c])
\`\`\`
Now the team (swarm) can be used similar to an agent:
\`\`\`python
result = team.run("Explain the importance of data privacy.")
print(result)
\`\`\`
Explain what might happen: "Here, all three agents will 'discuss' behind the scenes to answer the question. One agent might draft an answer, another might expand it, and another might refine it. The final output is a result that hopefully benefits from each agent's strengths."

(If possible, describe that Marvin coordinates this process automatically. If we know how: maybe each agent sees others' contributions as part of context or each tries in turn. But to avoid guessing, just state that they collaborate and Marvin handles merging their efforts.)

Also describe a scenario of a **structured Team** (non-swarm): maybe one agent delegates. For example: 
"A Team might also be set up where only a specific agent can delegate tasks to others (like a manager). While Marvin's API currently focuses on Swarm for free collaboration, conceptually you can design a workflow where Agent A asks Agent B for help, etc. In fact, Marvin agents themselves could call other agents as a kind of 'tool' if needed."

Clarify differences for users coming from ControlFlow: "In ControlFlow, you could assign multiple agents to a task and they would collaborate in a Plan. Marvin’s Swarm is a direct parallel [oai_citation_attribution:160‡pypi.org](https://pypi.org/project/marvin/3.0.0/#:~:text=,say), making multi-agent coordination easy to set up."

List best practices or caveats:
- **Use cases**: multi-agent shines in complex tasks: e.g., brainstorming (several creative agents generating ideas), double-checking work (one agent generates, another reviews), or handling multi-part tasks (one agent handles one aspect, another handles another).
- **Overhead**: note that multiple agents mean multiple LLM calls in the background, which can increase token usage and latency. So only use teams when the complexity warrants it.
- **Control**: If you want a deterministic process (e.g., always agent A then B then C), you might orchestrate that manually in code (like call A, then feed A's output to B, etc.) rather than using a free-for-all swarm. Marvin gives you tools to do both.
- **Teams vs Single Agent**: If one agent can do the job, keep it simple. Teams are for when diverse expertise or internal debate is needed.

Maybe provide a small theoretical outcome to illustrate: "In the above Swarm example, you might see output that is both concise and explanatory, because one agent enforced brevity while another added detail, and the third ensured quality."

Conclude by encouraging experimentation: "Multi-agent teams can sometimes achieve better results by combining perspectives. Marvin makes it easy to try this out – you can transform a single-agent solution into a multi-agent one by wrapping agents in a `Swarm` and running the same task."

Keep the explanation accessible. Since multi-agent can be abstract, use analogies: e.g., "It's like having a panel of AI assistants working together." Ensure that the user understands how to implement it (via `Swarm([...])` and `.run()` on it). 

How-To Guides – Summarize Text

Summary: This guide focuses on using marvin.summarize to condense text. Start by explaining the typical use-case: you have a long text and want a short summary or key points. marvin.summarize provides a one-call solution for that ￼. Mention that it’s one of Marvin’s high-level utility functions, which internally uses the same engine but is pre-tuned for summarization. Provide a quick example code snippet: feeding a few paragraphs of text to marvin.summarize and printing the summary. If possible, show the original text’s length vs the summary. Explain any options: perhaps marvin.summarize might accept parameters like length or style (if not, user can just instruct within the text or beforehand). Emphasize simplicity: it saves you from writing a full prompt like “Summarize the following…”, you just call the function. Also, mention that because this is backed by Marvin’s pipeline, it can output structured summaries too if asked (like summary in bullet points if you included that in instructions). Cover the scenario of summarizing different types of content: e.g., summarizing an article, a conversation (maybe mention if you can feed conversation logs and it will summarize them). Possibly mention summarizing code or logs (if applicable, although that might use same function or a variant). Provide one or two example uses: summarizing a block of text and summarizing multiple texts in a loop (to illustrate maybe mapping it). Keep it straightforward. The tone is helpful, focusing on the practical “here’s how to do it easily” angle. Since this is a guide, step-by-step is fine, but it’s a short process (just one function call essentially). You might also mention any limitations: e.g., very large text might need chunking (maybe suggest if text is extremely long, break it up since underlying LLM has context limits). End with suggesting the user try summarizing something from their own data as practice.

Prompt:

Write a how-to guide page **"Summarize Text"** for Marvin 3.

Introduce the purpose: "This guide shows how to use Marvin's built-in summarization utility to condense long text into a brief summary."

Explain in a sentence that `marvin.summarize` is a convenience function that takes in a piece of text and returns a concise summary [oai_citation_attribution:162‡github.com](https://github.com/PrefectHQ/marvin#:~:text=,Converse%20with%20an%20LLM).

Provide a code example right away:
\`\`\`python
import marvin

text = """
Marvin is an open-source toolkit that simplifies the process of building AI-powered software.
It provides high-level functions to summarize text, extract information, and more.
Marvin 3.0 combines the user-friendly design of its predecessor with a powerful new engine.
This allows developers to create robust AI workflows with minimal code.
"""
summary = marvin.summarize(text)
print("Summary:", summary)
\`\`\`
After the code, show (or describe) a possible output, e.g.:
*Output:* "Marvin is an open-source AI toolkit that makes it easy to build AI software, offering simple functions for tasks like summarization and extraction, now powered by a more robust engine in version 3.0."

Walk through what happened: "We passed a multi-sentence paragraph to `marvin.summarize`. Marvin returned a single concise sentence capturing the key point. The summarizer automatically knew to highlight Marvin being an AI toolkit with simple functions and a new engine."

Point out that you didn't have to write a prompt like "Summarize the following text:" – the function handled that for you. This saves time and ensures a consistent style of summary.

Mention any options or tricks:
- If you want a different style of summary (e.g., bullet points vs a sentence), you can either post-process or instruct slightly in the text (for instance, you could include in the text something like "Output as bullet points. \n\n {actual text}" – though that's a bit hacky).
- By default, it gives a concise summary; if the text is extremely long (several pages), Marvin will attempt to summarize it as best as possible, but for very long texts consider summarizing in chunks or increasing context window if using a bigger model.

Also, highlight that `marvin.summarize` works with any text content. Try another quick example (maybe as a secondary example or just describe): "For example, you can summarize an article fetched from a website, or summarize the content of a PDF (after you extract the text). It's a generic text summarizer."

Potentially mention: "Under the hood, this uses the same LLM that Marvin is configured with, so ensure your model has the capacity to handle the text length. For OpenAI's GPT-4, you can usually summarize a few thousand words effectively."

If Marvin’s summarizer has known behavior (like it might always output a certain style, or if it doesn't allow customization), note that briefly. But likely it's straightforward.

Conclude with a suggestion: "Whenever you find yourself needing a quick summary of something – whether it's a user message, a piece of documentation, or a long report – `marvin.summarize` provides a one-line solution."

Keep the style simple and instructional. The user reading this should quickly grasp how to use `marvin.summarize` from the example and explanation.

How-To Guides – Classify Data

Summary: This page shows how to use marvin.classify to categorize text or other data into predefined classes ￼. Explain that classification is useful for labeling content (e.g., tagging incoming messages as spam/ham, or sentiment analysis, etc.). Outline how marvin.classify works: likely you provide the input and also tell it what the possible classes are (maybe via a parameter or in the content? Marvin2 docs show providing labels list or enum). If the API is just marvin.classify(text, labels=[...]) we should illustrate that. If not certain, propose usage: either via special formatting or mention that marvin.classify will try to infer classes if the prompt indicates, but it’s safer to provide them. Possibly reference Marvin2 classification approach (they mention lists, Enums, etc.). Provide an example: classifying a support ticket as “bug”, “feature request”, or “other” using marvin.classify. Show the code snippet and output. Also show a simpler scenario: sentiment (positive/negative). Explain that behind the scenes, Marvin will prompt the LLM to pick one of the given categories based on the input, and then return that category (maybe as a string or index). If multiple classes are possible, mention if marvin.classify can return multiple or just one (likely one by design). Also mention data types: it might accept not just text but any data that can be described (but primarily text is likely). The style is like a mini-tutorial: “here’s how to do classification in one line.” Also cover best practice: define clear labels. Possibly mention that if using Enums or booleans, Marvin will adapt (like if you give a bool type as result_type maybe it does yes/no classification). Show an example with an Enum if applicable (based on Marvin2 docs “Providing labels” etc). But keep it straightforward for the new user: list-of-strings is easiest. Also caution that classification still uses LLM so it’s probabilistic; for very critical classification, maybe double-check borderline outputs. End with encouraging to use classify to quickly categorize lots of texts by looping or so.

Prompt:

Write a guide for **"Classify Data"** using Marvin 3’s `marvin.classify` function.

Start by explaining the purpose: "Marvin’s `classify` function allows you to automatically assign labels or categories to a piece of data (typically text) using an LLM. Instead of writing a prompt asking 'Is this X or Y?', you can just call `marvin.classify` and get a label back."

Illustrate with a simple example. For instance, classify the sentiment of a sentence:
\`\`\`python
import marvin

text = "I really love the new update, it's fantastic!"
label = marvin.classify(text, labels=["positive", "negative"])
print(label)  # Expected output: "positive"
\`\`\`
(This assumes `marvin.classify` takes a `labels` argument with possible categories. If not certain, you can describe that conceptually, like `marvin.classify` knows to output one of those labels.)

Explain: "We provided two possible labels: 'positive' or 'negative'. Marvin will analyze the text and return the label it best fits. In this case, the text clearly expresses love for the update, so the returned label would be 'positive'."

Discuss how you can specify labels:
- You can pass a list of strings representing categories (as above).
- You could also use an Enum type or Boolean for binary categories, depending on preference (e.g., `True/False` for yes/no classification; Marvin will then return a Python bool).
- If no labels are provided (not sure if allowed), Marvin might try to guess a label, but it's best to provide them to constrain the output.

Show another example, perhaps multi-class:
\`\`\`python
issue = "The app crashes when I try to upload a file."
category = marvin.classify(issue, labels=["bug", "feature request", "user error", "other"])
print(category)  # e.g., "bug"
\`\`\`
Explain: "Here we have an issue description. We want to categorize it as either a bug report, a feature request, user error, or other. Marvin will choose the best fitting category. Likely it will return 'bug' because the user reports a crash."

Mention how Marvin decides: It effectively asks the LLM to choose the most appropriate label given the content. The LLM has context of these labels and will output one of them. Marvin then returns it directly as a string (or the corresponding Enum/Boolean if that was used).

Tips:
- **Define clear categories**: The more distinct and well-defined your labels, the better the classification. Overlapping categories can confuse the model.
- **Case sensitivity**: Probably Marvin returns exactly one of the provided labels. You might want to ensure labels are distinct strings that don't overlap in wording.
- **Outputs**: Marvin will return one of the labels (or potentially a list if it thinks multiple apply? But likely one; if multiple classification is needed, you might run multiple calls or use a custom approach).
- **Confidence**: The LLM won't give a score, just a choice. If needed, you could run it multiple times or prompt it to check confidence (beyond scope of this simple function though).

Performance note: "Because classification uses the underlying LLM, it's suitable for moderate amounts of data. If you need to classify thousands of items quickly, an LLM might be slower and costly; Marvin is best used when you need the flexibility of AI understanding for classification tasks that simpler rules or models can't handle."

Wrap up by suggesting: "Use `marvin.classify` whenever you have a predefined set of categories and want the AI to do the sorting for you. It’s especially handy for things like triaging support tickets, sentiment analysis, tagging feedback, etc., without training a custom model."

Keep the instructions clear and the example outputs commented or described so the user knows what to expect. 

How-To Guides – Extract Information

Summary: This guide will show how to use marvin.extract to pull structured data out of unstructured text ￼. Explain that marvin.extract is designed for when you have some text and you know what kind of information you need from it, like dates, numbers, names, etc., and you want them as Python types (int, float, list, dict, etc.). Highlight that you usually provide the target type or schema. Provide an example: e.g., given a sentence with some numbers and currency, extract all integers (like the money example from README ￼ ￼) or extract a specific entity. Possibly do an example: “I paid $30 for 5 apples” extract int -> [30, 5]. Or a slightly complex one: “John Doe’s email is john@example.com” extract using a regex type or something – but simpler is better. Use the example from README for consistency:
marvin.extract("I found $30 and then spent $10", int, instructions="only USD") yields [30, 10] ￼ ￼. Show that and explain the usage: the second argument is the type of thing to extract (here int, could also be a custom Pydantic model to extract into a schema). Also mention you can specify instructions to narrow down what to extract (“only USD amounts”). Another example: extracting an email address to a str or a date to a datetime if possible (with the appropriate type from Python). Emphasize that marvin.extract will attempt to parse the text and produce instances of the target type. If the target is a list type or so, likely it returns a list of matches (like list[int] gave list of ints). Mention that if nothing is found, it might return an empty list or None (depending on type). Also point out this is like having an AI do information extraction for you without manual regex. The user can adjust prompt via instructions param if needed to clarify what to extract. End by encouraging use of extract for tasks like pulling out structured fields from user input, parsing logs for key info, etc. Possibly caution that the accuracy depends on the LLM understanding the text; for critical extraction (like legal or something), double-check results.

Prompt:

Write a guide page **"Extract Information"** describing how to use `marvin.extract` to retrieve structured data from text.

Begin with the scenario: "Often, you have unstructured text and you need to pull specific information out of it – like dates, prices, names, etc. `marvin.extract` simplifies this by letting the AI find and return exactly the pieces you want, in the data types you need."

Explain the basic usage: you call `marvin.extract(text, target_type)` where `target_type` is a Python type or schema representing what you want to extract [oai_citation_attribution:169‡github.com](https://github.com/PrefectHQ/marvin#:~:text=). The function returns data of that type (or containing that type).

Give a simple example (the one from Marvin's README):
\`\`\`python
import marvin

sentence = "I found $30 on the ground and bought 5 bagels for $10."
numbers = marvin.extract(sentence, int)
print(numbers)  # Expected: [30, 10]
\`\`\`
Explain: "We asked Marvin to extract `int` from the sentence. It returned a list of integers [30, 10] – all the integers it found (the dollar amounts in this case)."

Note: If the text had only one int, `marvin.extract` might return a single int; but since multiple were present, it returned a list of ints. (Marvin is smart about whether to return a single instance or list of instances depending on context.)

Show another example, perhaps extracting into a more structured type:
\`\`\`python
from pydantic import BaseModel

class Product(BaseModel):
    name: str
    price: float

text = "The new iPhone costs $999."
product_info = marvin.extract(text, Product)
print(product_info)
# Expected: Product(name='iPhone', price=999.0)
\`\`\`
Explain: "We defined a Pydantic model `Product` with a name and price. By using `marvin.extract` with `Product` as the target, Marvin will attempt to parse the sentence and fit the data into the Product schema. The result is a Product object with name='iPhone' and price=999.0."

Point out that this is powerful – with minimal effort, you got a structured object out of freeform text.

Cover **instructions** parameter: "If needed, you can give additional guidance via the `instructions` argument. For example, if you only want USD prices, or want dates in a certain format." Show a quick tweak:
\`\`\`python
text = "I have 3 cats and 2 dogs."
count = marvin.extract(text, int, instructions="just count animals")
print(count)  # Expected maybe [3, 2]
\`\`\`
(This might be trivial, but illustrate that instructions can clarify if needed.)

Mention edge cases:
- If the info isn't present, Marvin might return an empty list or a default value (depending on type).
- If multiple pieces of info are present and the target type is singular (not a list), Marvin might return the first or combine them – but usually using a list type as target is better if you expect multiple.
- It's not using regex or strict parsing – it's using AI understanding. This means it can handle subtle variations (like "$30" vs "30 dollars" both yield int 30). But also, it's not 100% deterministic; for critical extraction you might want to validate the results.

Highlight use cases: "Use `marvin.extract` to quickly get structured data from user inputs (e.g., extract an email address or extract numbers they mention), to parse logs or messages (like find all error codes in a log text), or to pre-process data for further computation."

Encourage experimenting: "If you have a custom data structure, just define it (with Pydantic or TypedDict or dataclass) and pass it in – Marvin will try to fill it out from the text. This can save a lot of manual parsing code."

Keep tone helpful. Make sure to note that this is one of Marvin's high-level functions built for convenience. 

How-To Guides – Transform Data Types

Summary: This guide covers marvin.cast for transforming unstructured input into a specified structured type ￼. Clarify how it’s different from extract: extract pulls info out, whereas cast takes a whole input and tries to fit it into a given structure. For example, converting a description into a structured object, or freeform text into a specific format. Provide example from README: using marvin.cast("the place with the best bagels", LocationTypedDict) to get lat/long ￼. In general, cast might be used when the entire input is describing an entity and you want a structured representation. Another example: cast “June 5, 2021” to a datetime.date or string in “YYYY-MM-DD” format. Emphasize that cast is like asking Marvin to reinterpret the input as a certain type. Show code: e.g.,

from typing import TypedDict
class Location(TypedDict):
    lat: float
    lon: float

result = marvin.cast("Eiffel Tower in Paris", Location)
# result -> {"lat": 48.8584, "lon": 2.2945}

(This is hypothetical but plausible if Marvin calls some geocoding knowledge or just known lat/lon, given an LLM it might know the coordinates or approximate). The README example did exactly that with bagels -> lat/lon of NYC presumably ￼. Use that. Also mention you can cast to simple types too: e.g., marvin.cast("twenty", int) might yield 20 (not sure if it does that, but possibly). Another scenario: cast “true” to bool True. So it’s like a smart type converter with AI help. The page should clarify that cast uses context from knowledge (LLM may actually know some facts like locations, or might guess from context). If the LLM doesn’t know, it might just do best effort. So results may vary on factual correctness if it’s not a trivial transformation.
Encourage use cases: formatting data, converting user input into programmatic types, etc. Possibly caution that for critical conversions (like addresses to coordinates), it’s not guaranteed accurate (LLM is not an actual geocoder, though might have training knowledge). Provide at least one code example and one demonstration of usage. End with some suggestions of what you can cast (numbers in words to digits, descriptions to structured records, etc.)

Prompt:

Write a guide **"Transform Data Types"** explaining how to use `marvin.cast` to convert or interpret input data as a desired type or schema.

Begin by explaining what `marvin.cast` is for: "The `cast` function takes an input (often text) that represents some data and converts it into a specified type or structure. It's like telling Marvin: 'Here's some information, give it to me in this format.'"

Highlight difference from extract: extraction pulls pieces out of text, whereas cast assumes the whole input is describing the thing you want to create.

Provide a straightforward example from the docs:
\`\`\`python
import marvin
from typing import TypedDict

class Location(TypedDict):
    lat: float
    lon: float

place = "the Empire State Building"
coordinates = marvin.cast(place, Location)
print(coordinates)
# e.g., {"lat": 40.748817, "lon": -73.985428}
\`\`\`
Explain: "We provided a place name and asked Marvin to cast it to a Location with latitude and longitude. Marvin knows (or can find out, from its training data) the coordinates of the Empire State Building, so it returned a Location dictionary with lat and lon." (Acknowledge that the LLM might not always be accurate for such factual info, but this example likely works since it's a famous landmark with known coordinates.)

Show another simple example: converting a textual number to an integer.
\`\`\`python
result = marvin.cast("one hundred twenty three", int)
print(result)  # 123
\`\`\`
Or a date:
\`\`\`python
from datetime import date
d = marvin.cast("July 4th, 2023", date)
print(d)  # datetime.date(2023, 7, 4)
\`\`\`
(If date is tricky, maybe skip, but ideally Marvin could parse it.)

Explain: "Marvin is effectively doing a natural language to structured data conversion. The model interprets 'one hundred twenty three' and outputs the integer 123. Similarly, it can parse common date formats into a Python date object."

Emphasize the variety of targets:
- Primitive types (int, float, bool, etc.): Marvin can convert descriptions or words into these.
- Complex types (TypedDict, Pydantic BaseModel, dataclasses): Marvin will attempt to fill in all fields appropriately if the information is present or inferable.
- Even lists or dicts: e.g., `marvin.cast("apple, banana, cherry", list[str])` might give `["apple", "banana", "cherry"]`.

Add guidance:
- The input should contain or imply the information needed for the target type. If something isn't specified, Marvin might guess or use general knowledge (e.g., if asked to cast "Mars" to a `Planet` model requiring distance from sun, it might fill it approximately from knowledge).
- If Marvin doesn't have enough info, results may be incomplete or it may just do its best. For example, casting "John Doe" to an `Person(name:str, age:int)` might give an age but it's just making one up unless context provides it.

Also mention that `marvin.cast` is used for format conversion, so if you have data in a string that needs to become a JSON or Python object, cast can help (though one could also use extract in some cases, cast is more direct when the whole input is the thing).

Use cases: "Use cast when you have freeform input that should become a structured object. For instance, user inputs their address in one field – you could cast that string to an Address model with separate street, city, zip fields (the LLM will parse it accordingly). Or converting natural language specifications into config objects, etc."

Wrap up with a note: "Marvin’s ability to cast data means you often don't need custom parsing code for messy inputs – just specify what you need, and Marvin will shape the data for you."

Tone should be instructive and optimistic about how this saves effort. Ensure the examples are clear and show the output format.

How-To Guides – Generate Data or Content

Summary: This guide explains marvin.generate function, which creates structured data from a description ￼. Emphasize that generate is for when you want the AI to produce examples or data items according to some pattern or type. For instance, generating a list of items meeting certain criteria (like in README example: generate 10 odd primes as ints ￼). Provide that example. Another use: generate dummy data for testing (like generate 5 fake user profiles as instances of a User model). So it’s about creative generation but structured. Show code:

primes = marvin.generate(int, 10, "odd primes")
print(primes)  # [3, 5, 7, 11, 13, 17, 19, 23, 29, 31]

￼. Explain the signature: maybe marvin.generate(type, count, description). Or maybe it’s marvin.generate(type, description) and it infers count from type if list? The example suggests first arg is type of elements, second arg is number to generate if type is singular? Not entirely sure, but from [18], it looks like:
marvin.generate(int, 10, "odd primes") returned a list of 10 ints. Possibly the API is generate(item_type, n, description) specifically for generating n items of that type based on description. We’ll assume that’s the case.

So document it accordingly:
	•	If you want multiple outputs, provide the count.
	•	If you want just one instance of some complex object, maybe count=1 or an optional param.

Anyway, illustrate multiple generation (like primes example) and maybe single generation:
E.g., “marvin.generate(str, 3, ‘names of fruits’)” -> [“Apple”, “Banana”, “Cherry”]. Or generate an object:

from pydantic import BaseModel
class Todo(BaseModel):
    task: str
    done: bool

todos = marvin.generate(Todo, 3, "to-do items")
# Example output: [Todo(task='Buy milk', done=False), Todo(task='Clean house', done=True), ...]

This shows structured generation.

Explain that it’s great for getting sample data, brainstorming lists, etc., all with type safety (the outputs conform to specified type). Mention that if the type is simple (int, str), result is a list of that type of length N. If type is complex model, result is a list of model instances.

If generate can be used for just one output, perhaps just call with count=1 or there’s an overloaded usage. If unclear, focus on the multi-generation use-case since that’s unique.

Caution that the quality of generated items depends on the description and the model’s knowledge/creativity. Great for creative tasks or test data generation.

Encourage trying different descriptions (like “fictional product names”, “test user accounts with realistic details”, etc).

Keep tone practical.

Prompt:

Draft the **"Generate Data or Content"** guide for Marvin 3, focusing on using `marvin.generate` to create structured outputs from a description.

Introduce what `marvin.generate` does: "This function asks the AI to *generate* one or multiple items of a specified type based on a description. It’s useful for creating sample data, test cases, or creative content in a structured form."

Explain the basic usage using the primes example:
\`\`\`python
import marvin

# Generate 10 odd prime numbers
primes = marvin.generate(int, 10, "odd primes")
print(primes)
# Output: [3, 5, 7, 11, 13, 17, 19, 23, 29, 31]
\`\`\`
Describe: "We asked for 10 odd primes as integers. Marvin returned a list of 10 int values that are indeed odd prime numbers. We didn't have to code the logic for primes – the AI provided them correctly."

Break down the function parameters (based on how it appears):
- The first argument is the type of item to generate (`int` in this case).
- The second argument is the number of items we want.
- The third argument is a short description of what we want generated.

So the call basically reads as: "Generate `<count>` `<type>` that satisfy `<description>`."

Show another example, generating strings:
\`\`\`python
colors = marvin.generate(str, 5, "names of green fruits")
print(colors)
# Possible output: ["Apple", "Kiwi", "Grapes", "Avocado", "Pear"]
\`\`\`
Explain: "We requested 5 names of fruits that are green. Marvin came up with a list of fruit names, all typically green in color. It's essentially doing a creative brainstorm within the constraints given."

Demonstrate generating complex objects:
\`\`\`python
from pydantic import BaseModel

class Person(BaseModel):
    name: str
    age: int
    city: str

people = marvin.generate(Person, 3, "random fictional individuals")
for p in people:
    print(p)
# Example output:
# Person(name='Alice', age=29, city='London')
# Person(name='Bob', age=41, city='New York')
# Person(name='Charlie', age=35, city='Sydney')
\`\`\`
Explain: "We defined a `Person` model with name, age, and city. By asking Marvin for 3 random fictional individuals, we got a list of Person objects with plausible data. This is great for generating dummy data or examples."

Points to emphasize:
- **Structured output**: Unlike a typical prompt that might give you a single blob of text, `marvin.generate` returns actual Python objects of the type you specified (or a list of them). This means you can directly use the results in your code (loop through them, access attributes, etc.).
- **Guidance**: The description you provide guides the content. Be as specific or as general as you want. For example, "fantasy character names" vs "common English first names" would yield different outputs.
- **Count**: You can generate as many items as needed, but remember more items = longer output and more work for the AI. If you ask for 100 items, ensure your model context can handle that.
- **Quality**: The AI uses its knowledge to generate data. For factual lists (like prime numbers), it can be surprisingly accurate. For creative or subjective lists (like "interesting startup ideas"), it's providing plausible invented content.
- **Use cases**: Quickly populating a prototype app with data, getting brainstorming lists (ideas, names, etc.), generating test cases (like test sentences or scenarios) without manually coming up with them.

Also mention: If you only want one item, you could still use `marvin.generate(Type, 1, "description")` and get a list of one element (just take [0]). Or maybe there's a variant that returns a single item if count is omitted (not sure, but not critical).

Conclude by encouraging to try different descriptions: "This function is a handy way to leverage the AI for creative or tedious data generation tasks. Just describe what you need and how many, and let Marvin do the rest."

Keep the style instructional and show excitement about not having to hand-craft this data or logic. 

How-To Guides – Conversational AI (Chat)

Summary: This guide focuses on using marvin.say for conversation or interactive chat ￼. Explain that marvin.say is like having a quick chat with the AI: you give a user message and it returns a response, possibly keeping persona or context in mind. Provide an example:

reply = marvin.say("Hi Marvin, how are you?")
print(reply)  # "Hello! I'm doing well, thanks for asking..."

It likely produces a friendly greeting. Emphasize that unlike marvin.run which might be used for one-off tasks, marvin.say might be tailored for conversational use-cases (though in code they may be similar, but conceptually it’s for dialog, maybe automatically using a default chat agent persona like a helpful assistant). Mention that if used inside a Thread, it will keep context so you can do multi-turn chat easily by calling marvin.say repeatedly within the same thread (or using the CLI with marvin.run(..., cli=True)). If Marvin has an “Assistant” concept, perhaps marvin.say uses a default assistant agent with an open-ended style. Also mention customizing conversation: maybe you can pass a style or persona argument, or that you would instead create a custom agent and use agent.run for a different persona, but marvin.say might just use a general one.

Show a brief conversation example:

with marvin.Thread() as convo:
    print(marvin.say("What is the capital of France?"))  # "The capital of France is Paris."
    print(marvin.say("What is the weather like there?"))  # uses context to know "there" means Paris.

This shows multi-turn in one thread using say.

Advise that for building chatbots, one might use a loop reading user input, calling marvin.say, etc., or incorporate memory for persistent sessions. Possibly mention that Marvin 3 integrated well with CLI (as earlier CLI page covers interactive usage).

Also highlight differences from high-level functions: say doesn’t require specifying a structured output or label – it’s freeform conversation, akin to typical chat with an AI assistant.

Encourage using say for Q&A, small talk, or whenever you just want a direct answer with no special formatting.

Prompt:

Write the **"Conversational AI (Chat)"** guide for Marvin 3, focusing on `marvin.say` and how to have interactive exchanges.

Start by explaining that Marvin can be used as a conversational assistant, not just a one-shot question-answer. The `marvin.say` function is a convenient way to get a conversational response from the AI [oai_citation_attribution:177‡github.com](https://github.com/PrefectHQ/marvin#:~:text=,AI%20functions%20without%20source%20code).

Give a simple example:
\`\`\`python
import marvin

response = marvin.say("Hello, Marvin! What's your purpose?")
print(response)
\`\`\`
Output might be something like:
*"Hi there! I'm Marvin, an AI toolkit designed to help developers build smart applications. I can answer questions, summarize text, and much more – I'm here to make AI integration easier!"*

Explain: "When you use `marvin.say`, you're effectively chatting with Marvin’s default assistant agent. It will respond in a friendly, helpful manner to whatever prompt or question you give."

Point out that this is similar to `marvin.run`, but conceptually it's geared towards free-form dialogue (no specific structured output or task instructions needed, just conversation).

Now demonstrate a multi-turn conversation. Use a thread to maintain context:
\`\`\`python
with marvin.Thread() as chat:
    user1 = "I'm planning a trip to Japan. What are some must-see sights?"
    reply1 = marvin.say(user1)
    print("Marvin:", reply1)

    user2 = "Great! And how should I prepare for the language barrier?"
    reply2 = marvin.say(user2)
    print("Marvin:", reply2)
\`\`\`
Describe what's happening: "We start a conversation thread and ask Marvin a question about traveling to Japan. Marvin might list a few famous attractions (Mount Fuji, Tokyo Tower, Kyoto temples, etc.). Then we ask a follow-up question about language – because this is in the same thread, Marvin remembers we're talking about a trip to Japan and can tailor its answer accordingly (maybe suggesting learning some basic phrases or using translation apps)."

Explain how context works here: if `marvin.say` is used inside a Thread, it has memory of previous `marvin.say` calls in that thread, so it can maintain a coherent conversation. If you call `marvin.say` on its own, it's just a single-turn response (no memory of anything before unless you manage it).

Advise for building chatbots:
- You can loop reading user input and calling `marvin.say(input)` each time within a persistent thread to maintain a session.
- You might want to define a custom agent for a specific persona or role. For example, if you want Marvin to be a snarky chatbot or a specific character, you could create an Agent with those instructions and then use `agent.run()` for conversation. (So `marvin.say` uses a default friendly agent, but you have the flexibility to customize if needed.)

Mention that `marvin.say` under the hood likely calls the same LLM, just with a conversational style. It's an alias for convenience.

Optionally, discuss any formatting or special behavior: e.g., does `marvin.say` always produce just a message string (likely yes). If the conversation requires structured data or actions, you'd use other functions or tools, but `say` is for plain dialogue.

End with: "Using `marvin.say` is the quickest way to interact with Marvin as if it were a chatbot. Whether it's for a Q&A scenario, an interactive assistant in your app, or just testing out ideas, this function makes it easy to get a conversational response."

Keep the tone approachable, as if explaining how to talk to the AI. 

Additional Modalities – Generate Images

Summary: This page explains how to generate images using Marvin’s capabilities (likely via an integration like DALL-E or Stable Diffusion). Possibly marvin.ai.images.create_image(prompt) exists. We should treat it as a guide similar to the text ones but focusing on how to produce an image given a text prompt. Provide example usage if possible:

image = marvin.create_image("a sunset over the mountains")
image.save("sunset.png")

If Marvin returns an image object or URL. Or maybe marvin uses stable diffusion API, we need to guess. The Marvin2 docs had “Creating images” page – likely instructing to provide a prompt and it returns maybe an image (maybe as base64 or PIL image?). We don’t have that detail, but we can say Marvin supports generating images through connected image models. Perhaps Pydantic AI could include image models or Marvin might call out to OpenAI’s image API if an API key is set.

Anyway, mention that to use image generation, you might need to configure an API (like stability or replicate). If Marvin uses stable diffusion via HuggingFace, might need an API token or library. If we want to not guess too deep, just say Marvin can create images if properly configured.

Focus on how to write a good prompt for image, and how to handle the output (like display or save it). If running in code, maybe the output could be a file path or an image object.

Use caution to not promise specifics we don’t know. Possibly refer to “marvin.ai.images” module (which existed in Marvin2). The API might be something like marvin.ai.images.create(prompt: str) -> bytes or Image.

However, since it’s a plan, maybe we outline that such capability exists and user should refer to installation of needed model or keys.

Prompt:

Write the **"Generate Images"** guide for Marvin 3, explaining how to use Marvin to create images from text prompts.

Start by noting that Marvin can interface with image generation models (like DALL-E or Stable Diffusion) to produce images based on a description. It's a powerful feature for creating visual content from code.

Explain prerequisites: "To use Marvin’s image generation, you may need to configure an image model provider. By default, Marvin might use OpenAI’s image API if an OpenAI API key is provided (for DALL·E), or other providers if configured. Ensure you have the necessary API access or models available."

Show a basic example:
\`\`\`python
import marvin

# Generate an image of a sunset over mountains
image = marvin.create_image("a beautiful sunset over snow-capped mountains")
# Save the image to a file
with open("sunset.png", "wb") as f:
    f.write(image)
\`\`\`
(This assumes `marvin.create_image` returns image bytes or a PIL image; if it's a bytes object, writing to file is one way. If it's a PIL Image, you would do `image.save("sunset.png")`. We can mention either approach.)

Explain: "In this example, we provided a prompt describing the desired image. Marvin's image generation function processed the prompt through an underlying image model and returned image data (in this case, we saved it as a PNG file)."

Mention that you can adjust parameters if supported:
- Perhaps image size, style, or number of variations, if Marvin’s API allows (for instance, `marvin.create_image(prompt, width=512, height=512)` or similar). If not sure, just say some models allow controlling resolution or number of outputs, and Marvin might expose those via optional parameters.

Talk about **prompt crafting**: "When generating images, the description (prompt) is crucial to get the result you want. Be specific about subjects, scenery, style, and any details. For example, 'a pencil sketch of a cat riding a bicycle, comic style' will yield a very different image than 'a photorealistic cat on a bicycle at sunset'. You can experiment with the phrasing to guide the model."

If Marvin supports multiple images or variations:
- Possibly mention if you can get more than one image (like `marvin.create_image(prompt, n=3)` to get 3 variations, if that exists).
- How to handle or view those (like saving or displaying if in a notebook).

Also advise on **performance**: "Image generation can be slower than text, and might have additional costs (e.g., using OpenAI’s image API costs per image). Marvin will wait for the image to be generated, which could take a few seconds."

And **limitations**:
- Generated images might not always perfectly match the prompt (common in generative models).
- If the prompt violates content guidelines (e.g., violent or NSFW), the underlying service might reject it or modify it. Stay within acceptable use.
- The quality depends on the model behind the scenes (OpenAI's DALL-E tends to produce decent results for many prompts; stable diffusion can produce high-quality images especially if fine-tuned prompts and possibly using certain model versions).

Conclude with: "Image generation in Marvin opens up creative possibilities – you can dynamically create visuals within your applications. For example, generating an image on-the-fly in response to user input or creating illustrative images for generated text content."

Encourage trying various prompts and iterating to see what results you get.

Keep language straightforward. Since image generation can vary widely, focus on the process (prompt in, image out, and how to use it) rather than guaranteeing any specific output.

(We would continue similarly for “Caption Images”, “Transcribe Speech”, etc., following the patterns of the Marvin 2 docs, but for brevity, assume similar detail is provided for each.)

Style Guide

To ensure consistency and quality across Marvin 3’s documentation, we will adhere to a clear style guide:
	•	Tone and Voice: Use a friendly, professional tone with an encouraging and instructive voice. The docs should feel like a helpful expert guiding the user. Write in second person (“you”) to directly address the reader ￼. Avoid overly formal or academic language; keep it conversational but concise (similar to ControlFlow’s approachable style). We strive for an empowering tone – e.g., “you can easily do X with Marvin” – to make users feel confident.
	•	Clarity and Simplicity: Favor short sentences and clear explanations. Break down complex ideas into step-by-step reasoning or bullet lists. Assume the reader knows Python but may not be familiar with Marvin or LLM concepts. Define jargon on first use (e.g., “Large Language Model (LLM)”) and use abbreviations thereafter. If referencing concepts from Marvin 2 or ControlFlow, briefly explain them in Marvin 3 terms to avoid confusion.
	•	Structure and Formatting: Follow a consistent hierarchy of headings (H2 for major sections, H3 for subsections, etc.) across pages. Each page starts with a brief introduction or overview of the topic before diving into details or examples. Use bold to highlight key terms or important notes (but sparingly). Use italics for emphasis or defining new terms. Inline code should be in backticks (`marvin.run`) when referring to code elements ￼. Longer code examples go in fenced code blocks with language hints for syntax highlighting. After code examples, provide a short explanation or expected output in text or as a commented line, to help the reader understand the result without running it.
	•	Examples and Snippets: Every concept or guide page should include at least one concrete example. These examples should be self-contained and focused on illustrating the point. Use realistic values in examples (e.g., actual prompts, meaningful data) so users can directly try them. When showing output, either use a block quote or a comment to differentiate it from code. Ensure example code has been tested or reasoned about for correctness relative to Marvin’s behavior. If using placeholders (like an API key), clearly indicate that in the text (e.g., "YOUR_API_KEY").
	•	Cross-References: Encourage navigation by referencing related sections. For instance, if a guide touches on something explained in Core Concepts, include a phrase like “(as discussed in the Tasks section)” with a link to that page. This helps users find more information easily. Keep link text descriptive (e.g., “see the Memory section” rather than “click here”). Use consistent names for sections and features (always capitalizing proper nouns like Thread, Agent when referring to Marvin classes, to distinguish from general concept of an agent).
	•	Consistent Vocabulary: Use Marvin’s terminology consistently. For example, always use “Thread” (capital T) when referring to Marvin’s context manager, to match the class name, but you might say “workflow” in a general sense. Similarly use backticks or quotes around function and parameter names (marvin.fn, “tools” parameter) so they stand out. Refer to the user as “you” and Marvin as “Marvin” (not “we” for Marvin; reserve “we” for the docs voice guiding the user, but even then prefer direct “you”). Avoid ambiguous pronouns – when discussing multiple entities like agents and tasks, repeat the noun if needed to be clear which “it” you mean.
	•	Documentation of Code Behavior: Document what functions and classes do in a practical way. Instead of regurgitating a function signature, explain its behavior or purpose. For instance, rather than just “marvin.extract(text, type) extracts information,” say “marvin.extract finds pieces of data in text and returns them as the specified type.” If referencing source code or implementation details, do it only to clarify behavior, not to dump code in docs. Where relevant, cite external references (like ControlFlow or Pydantic AI docs) if they provide more depth, but keep Marvin’s docs self-contained for common usage.
	•	Visual Style: Keep pages visually clean. Utilize whitespace – in Markdown that means not overloading paragraphs. Use lists or tables for comparisons or option listings. For important warnings or tips, use callouts/admonitions if the docs system supports it (e.g., a Note: or Warning: block). For example, “Note: Marvin will throw an error if no API key is set, as the LLM cannot be accessed.” These should be used consistently (perhaps styled in a colored box by Mintlify) to draw attention.
	•	Example Data and Personas: Use coherent example scenarios across the docs where possible. For instance, we often talk about “writing a poem” or “summarizing an article” – reuse these contexts to reinforce understanding. ControlFlow’s docs use consistent sample names and tasks (like writing a poem in quickstart ￼). We can adopt a similar approach (e.g., always use a few recurring characters or themes in examples, like Alice and Bob for people, or a running theme of building a travel assistant in various sections). This gives continuity and makes the docs feel cohesive.
	•	Localization and Units: When presenting code or examples, use a neutral locale unless demonstrating localization features. For units and formats (dates, currency), stick to one style for consistency in examples (e.g., USD for money, ISO format for dates or a clearly specified format).
	•	Accessibility: Ensure that content is accessible: explain diagrams or images with alt text (if any images are used, provide descriptive captions). Avoid color-dependent meaning in text (since mostly Markdown text, this is fine). And keep language simple for non-native English readers – prefer common words over rare synonyms.
	•	Inspiration from ControlFlow: We emulate ControlFlow’s documentation language which was clear and developer-focused ￼. For instance, ControlFlow docs often start sections with a one-liner definition and then bullet points of what that concept enables ￼. We will adopt that pattern: opening each concept page with a crisp definition followed by key points, then dive into usage. ControlFlow also uses encouraging language (“allows you to… without sacrificing…” ￼); we will similarly highlight Marvin’s benefits in positive terms.

By following this style guide, all documentation pages will read as parts of a unified whole. Readers should be able to skim and identify important pieces (through consistent headings and formatting), and deeper reading will reveal a coherent, friendly narrative that aligns with Marvin’s ethos of being a lightweight but powerful toolkit.

Usability Focus

Marvin 3’s documentation is designed with user experience as a top priority. Here are key principles and measures we incorporate to maximize usability and accessibility:
	•	Progressive Discovery: The sitemap is organized to guide users from basic to advanced. New users can start with the Introduction and Quickstart to get instant gratification (a working example in minutes), then gradually learn Core Concepts with clear explanations and examples, before moving to advanced guides. Experienced users can jump straight into a specific section (like Configuration or a how-to guide) thanks to descriptive section titles and an intuitive grouping of topics. This dual-path approach ensures both newcomers and veterans find what they need quickly.
	•	Example-First Approach: We recognize that developers often learn by example. Each page (especially guides and concepts) begins or includes concrete examples of usage, so a reader can often copy-paste and try it out immediately. By seeing actual code and output, users gain understanding faster and with less confusion. For instance, instead of reading a long theoretical description of how to attach tools, they see a code snippet doing it and a brief explanation—making the learning experience more interactive and less frustrating.
	•	Addressing Common Pain Points: Many Marvin users may be coming from more complex or “bloated” LLM frameworks. We explicitly address their likely pain points:
	•	Setup complexity: In bloated toolkits, just getting started can be a chore. Our docs streamline this with a minimal Installation page and a Quickstart that shows something working in one or two lines, showcasing Marvin’s light footprint. This immediately answers the question “How hard is it to get something running?” with “Not hard at all – look!” ￼.
	•	Steep learning curve: We break down concepts into digestible pieces (one concept per page, with cross-links). If someone is used to a complex DAG of prompts in another toolkit, they’ll see Marvin’s approach (e.g., using a simple Thread context instead of a complicated flow graph) and how it achieves the same goal with less ceremony. We make those comparisons (without naming other tools negatively) by highlighting simplicity: e.g., “In Marvin, you don’t need to define a bunch of classes or YAML configs – a with-block and function calls get the job done.”
	•	Lack of transparency: Developers often struggle when a toolkit hides too much. We emphasize Marvin’s transparency and control. The docs frequently note how you can observe what’s happening (via logs, etc.), and that Marvin’s abstractions correspond to clear behaviors (for example, explaining exactly what context a Thread shares, or how tasks log their tool usage). This helps users trust Marvin because they can mentally model what it’s doing.
	•	Integration with existing code: We assume users have existing Python projects and want to inject LLM capabilities without rewriting everything. Many examples therefore show Marvin functions being used inline or Marvin cooperating with normal Python types (pydantic models, dataclasses, etc.). We stress that Marvin “plays nice” with standard Python – e.g., returning real Python objects from AI functions – which resolves the pain of some toolkits that return only strings that you then have to parse.
	•	Performance concerns: While Marvin is high-level, if there are tips to optimize (like not generating too many items at once, or how to handle large text by summarizing in parts), we include those as side notes. This anticipates user concerns about efficiency that might come from experiences with less efficient frameworks.
	•	Navigation and Searchability: Every page has a clear title and the sitemap is structured logically (mirroring ControlFlow’s intuitive nav categories ￼). We also use consistent terminology so that search (either built-in or via Ctrl+F) yields results – e.g., always calling the feature “Threads” not sometimes “Flows”, so users searching for “thread” find the right page. Where a concept might be known by different names from other contexts (e.g., “memory” vs “context history”), we mention both to capture those looking for either term. Additionally, linking related topics prevents dead-ends; if a user lands on the Tools page but really wanted to know about using them in a workflow, a pointer directs them to the Threads or Planning page seamlessly.
	•	Feedback Incorporation: We will encourage user feedback on the docs (perhaps via the community link or a “Suggest Edit” if Mintlify supports). The documentation plan itself considered common questions from Marvin’s user base (e.g., how do I do X that I did in ControlFlow or LangChain?). By preemptively answering these in the docs (like the Migration guide or explicit mention of how Marvin maps to ControlFlow concepts ￼), we reduce the need for users to ask or hunt for answers elsewhere. This makes the documentation self-sufficient and user-focused.
	•	Accessibility & Formatting: The documentation will follow best practices for accessibility: clear headings, lists for step-by-step instructions, and code examples that are easy to distinguish. We avoid large walls of text – paragraphs are 3-5 sentences max as a rule, which improves readability especially on screens. Important points are called out (using bold or note admonitions), so users scanning the page can catch key warnings or tips. The language is kept straightforward; where necessary to use a technical term, we explain it or ensure context makes it understandable.
	•	Consistency with ControlFlow (Familiarity): For users coming from ControlFlow, the docs feel familiar in structure and naming, easing their transition (core concepts have similar names, and the Migration guide explicitly maps old to new ￼). For new users, that consistency just translates to a coherent story, since ControlFlow’s docs were well-regarded – we leverage their proven structure while focusing on Marvin’s specifics.

In summary, every aspect of Marvin 3’s documentation is crafted to make the developer’s life easier. From the first “aha, it works!” moment in Quickstart, through deeper understanding of how to harness Marvin’s power, to troubleshooting and advanced use – the docs will serve as a friendly mentor. By prioritizing clarity, examples, and logical flow, we ensure users spend more time building with Marvin and less time struggling to understand how. The ultimate goal is that Marvin 3 feels intuitive and accessible, even to those frustrated by other tools, and the documentation is a key part in delivering that experience.