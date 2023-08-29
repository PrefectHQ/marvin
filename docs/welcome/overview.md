# The Marvin Docs

![](/img/heroes/life_the_universe_and_ai.png)

Marvin is a collection of powerful building blocks that are designed to be incrementally adopted. This means that you should be able to use any piece of Marvin without needing to learn too much Marvin-specific information.

For most users, this means they'll dive in with the highest-level abstractions, like AI Models and AI Functions, in order to immediately put Marvin to work. However, Marvin's documentation is organized to start with the most basic, low-level components in order to build up a cohesive explanation of how the higher-level objects work.

## Layout

### [Configuration](/configuration/settings/)

Details on setting up Marvin and configuring various aspects of its behavior, including LLM providers.

### [AI Components](/components/overview/)

Documentation for Marvin's "AI Building Blocks:" familiar, Pythonic interfaces to AI-powered functionality.

- AI Model: a drop-in replacement for Pydantic's `BaseModel` that can be instantiated from unstructured text
- AI Classifier: a drop-in replacement for Python's enum that uses an LLM to select the most appopriate value
- AI Function: a function that uses an LLM to predict its output, making it ideal for NLP tasks
- AI Application: a stateful application intended for interactive use over multiple invocations

### [OpenAI API Utilities](/llms/llms/)

Marvin exposes a simple API for building prompts and calling LLMs, designed to be a drop-in replacement for OpenAI's Python SDK (but with support for other providers).

### Examples

Finally, for deeper dives into how to use Marvin, check out our examples like the [Slackbot](/examples/slackbot/) or [GitHub Activity Digest](/examples/github-activity-digest/).
