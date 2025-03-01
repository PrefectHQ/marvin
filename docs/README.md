# Marvin Documentation

This directory contains the documentation for Marvin, a Python framework for building AI applications with LLMs.

## Documentation Structure

The documentation is organized into the following sections:

### Core Concepts

- [Tasks](concepts/tasks.mdx) - The fundamental building blocks of AI workflows
- [Agents](concepts/agents.mdx) - Specialized AI workers with different roles and capabilities
- [Threads](concepts/threads.mdx) - Maintaining conversation context across multiple interactions
- [Teams](concepts/teams.mdx) - Coordinating multiple AI agents to solve complex problems
- [Tools and Context](concepts/tools-and-context.mdx) - Extending AI capabilities with custom functions and additional information
- [Memory](concepts/memory.mdx) - Enabling agents to remember information across conversations

### Functions

- [run](functions/run.mdx) - Execute a task with an LLM
- [classify](functions/classify.mdx) - Categorize content into predefined classes
- [extract](functions/extract.mdx) - Pull structured data from unstructured text
- [cast](functions/cast.mdx) - Convert content to a specified structure
- [generate](functions/generate.mdx) - Create structured data or content
- [summarize](functions/summarize.mdx) - Create concise summaries of content
- [say](functions/say.mdx) - Have conversational interactions with an LLM
- [plan](functions/plan.mdx) - Create structured plans for complex tasks
- [fn](functions/fn.mdx) - Create AI-powered functions with a decorator

### Guides

- [Installation](installation.mdx) - Install Marvin and set up your environment
- [Quickstart](quickstart.mdx) - Build your first AI application in minutes
- [Configure LLMs](guides/configure-llms.mdx) - Use different LLM providers with Marvin
- [Configuration](guides/configuration.mdx) - Configure Marvin using environment variables and settings
- [Building a Multi-step Workflow](guides/multi-step-workflow.mdx) - Create a complete AI application with multiple connected steps
- [Building a Conversational Assistant](guides/building-a-chatbot.mdx) - Create a personalized chatbot with memory
- [Migration Guide](guides/migration-guide.mdx) - Upgrade to Marvin 3.0 from previous versions

### Patterns

- [Memory](patterns/memory.mdx) - Patterns for using memory in your applications
- [Tools](patterns/tools.mdx) - Patterns for creating and using tools
- [Task Results](patterns/task-results.mdx) - Working with structured task results
- [Running Tasks](patterns/running-tasks.mdx) - Different ways to run tasks
- [Instructions](patterns/instructions.mdx) - Crafting effective instructions
- [Interactivity](patterns/interactivity.mdx) - Building interactive applications

## Contributing to Documentation

If you'd like to contribute to the documentation:

1. Make your changes or additions following the existing format and style
2. Use clear, concise language and provide practical examples
3. Submit a pull request with your changes

## Building the Documentation

The documentation uses [Mintlify](https://mintlify.com/) for rendering. The configuration is in the `mint.json` file.

## Documentation TODOs

- Add more examples and use cases
- Expand multi-modal capabilities documentation as they are implemented
- Add more integration guides with other frameworks and services 