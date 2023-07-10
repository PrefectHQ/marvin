# Docs Overview

Marvin is a collection of powerful building blocks that are designed to be incrementally adopted. This means that you should be able to use any piece of Marvin without needing to learn too much extra information: time-to-value is our key objective. 

For most users, this means they'll dive in with the highest-level abstractions, like AI Models and AI Functions, in order to immediately put Marvin to work. However, Marvin's documentation is organized to start with the most basic, low-level components in order to build up a cohesive explanation of how the higher-level objects work.

## Organization

### Configuration
This section describes how to set up Marvin and configure various aspects of its behavior.

### Utilities
This section describes Marvin's lowest-level APIs. These are intended for users who want a specific behavior (like working directly with the OpenAI API, or building custom prompts).

- OpenAI: Marvin provides a drop-in replacement for the `openai` library, adding useful features and configuration (like logging and retries) without changing the API.
- Prompt Engineering: documentation of Marvin's prompt API, which uses Pythonic objects instead of templates munging.

### AI Components
Documentation for Marvin's "AI Building Blocks:" familiar, Pythonic interfaces to AI-powered functionality.

- AI Model: a drop-in replacement for Pydantic's `BaseModel` that can be instantiated from unstructured text
- AI Function: a function that uses an LLM to predict its output, making it ideal for NLP tasks
- AI Choice: a drop-in replacement for Python's enum that uses an LLM to select the most appopriate value

### Deployment
Documentation for deploying Marvin as a framework.