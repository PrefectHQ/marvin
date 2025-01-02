Okay, I understand. I'm ready to receive direct edit capabilities and will use them responsibly to browse the codebase and documentation as needed. I also appreciate the need for a detailed guide to ensure consistency and quality as I adapt the ControlFlow documentation for Marvin.

Here's a comprehensive "Documentation Conversion Guide" that outlines everything I need to know to effectively convert ControlFlow docs to Marvin docs.

# Marvin Documentation Conversion Guide

This guide outlines the principles, guidelines, and best practices for converting existing ControlFlow documentation into Marvin documentation. It covers everything from core stylistic choices to subtle but important code conventions.

## I. Core Principles

### 1. Focus on Developer Delight

*   **User-Centric:** Marvin is designed to be delightful for developers. This means prioritizing user experience and making things as intuitive and seamless as possible. Documentation should reflect that.
*   **Practicality:** Focus on how developers can use Marvin to solve real-world problems with code that can be copy-pasted.
*   **Clarity:** Use precise language, avoiding ambiguity and jargon, to explain all of Marvin's features, so users at any experience level can use Marvin.
*   **Conciseness:** Be brief and direct, and prefer short examples.
*   **Completeness:** Although we should be brief, the documentation is the only source of truth for Marvin, so be sure not to skip over important details that may have subtle effects.
*   **Actionable:** Users should be able to quickly understand *how* to use Marvin, and should be able to start prototyping quickly.

### 2. Prioritize Clarity and Conciseness

*   **Simple Language:** Use plain English and avoid overly complex sentences.
*   **Active Voice:** Prefer active voice for direct and concise communication.
*   **Avoid Jargon:** Explain all technical terms, or link to relevant definitions in the glossary.
*   **Precise Terminology:** Use consistent and accurate terms when describing concepts and features.

### 3. Examples are Key

*   **Real-World:** Emphasize practical use cases and scenarios.
*   **Copy-Pasteable:** All code examples should be fully functional and ready to run out of the box. Users should be able to copy the code and run it in their Python interpreter.
*   **Well-Commented:** Each line should have clear and concise comments that explain its purpose.
*   **Clear Output:** Include well-formatted output examples for every code block (either as a commented block at the end, or a separate text result).
*   **Concise Code:** Prefer the simplest code that clearly demonstrates the feature.

### 4. Marvin-First, Not ControlFlow-Second

*   **Marvin as Primary:** When explaining concepts, always start from a Marvin perspective and how they work in Marvin, not in ControlFlow.
*   **Implicit Conversion:** Do not use phrases like "adapted from ControlFlow" or "similar to ControlFlow", except when specifically highlighting the differences between a concept in ControlFlow and Marvin (for example, we'll need to explain how `Thread` replaces `Flow`).
*   **Focus on Evolution:** If you must mention ControlFlow, do so as a way of indicating how Marvin improves or extends previous concepts, while still using Marvin's terminology throughout.
*   **Avoid Redundancy**: Do not assume the user has any prior knowledge of ControlFlow.

### 5. Async-First

*   **Async is Core:** Emphasize that Marvin’s primary API is asynchronous and built around `asyncio`.
*   **Sync as Convenience:** Present the synchronous versions of functions as helper utilities for quick scripts and demos.
*   **Async Examples:** Whenever possible, show examples using `async` functions and methods, making the core message explicit.
*   **Explain Async:** Add a note in the "key concepts" section of each guide that explains how asynchronous code is being used.

## II. Specific Guidelines

### 1. Core Concepts

*   **Tasks:**
    *   Explain tasks as the fundamental unit of work in Marvin.
    *   Focus on the `Task` class and its properties.
    *   Emphasize `instructions` and `result_type`.
    *   Show how tasks can incorporate `tools`, `agents`, and `context`.
    *   Clearly explain `result_validator` and its purpose.
    *   Use simple examples to show how to use tasks.
    *   Explicitly avoid using `depends_on` as a property of a task.
*   **Agents:**
    *   Explain how agents are the entities that execute tasks, and how they are configured.
    *   Focus on the `Agent` class, including its `name`, `instructions`, `tools`, `model`, and `interactive` properties.
    *   Show how agents can be assigned to tasks and how to create specialized agents for a variety of purposes.
    *   Emphasize the "portable" nature of Agents as configurations for LLM usage.
    *   Clearly demonstrate that agents can be created and used in multiple flows and tasks.
*   **Threads:**
    *   Explain how Threads are used to maintain a conversational context, and describe how Marvin threads are different from a standard Python thread.
    *   Emphasize that Marvin will automatically instantiate a thread for you unless you want to explicitly manage thread state.
    *   Focus on how threads are used to maintain state and history, so agents can reason across multiple interactions.
    *   Use the `with` statement as the idiomatic approach to using threads.

### 2.  Functionality-Specific Documentation
*   **Result Types:**
    *   Explain the variety of options for `result_type` (e.g., `str`, `int`, `bool`, `list`, `dict`, Pydantic models, `Literal`, `Enum`, `None`).
    *   Provide clear examples of how to use structured types with Pydantic models and lists.
    *   Emphasize that `result_type` can also be used as a simple type converter in addition to validating a result type.
    *   Demonstrate the "labeling" or "classification" task type, which makes use of literals or enums as choices.
    *   Explain the purpose of `result_validator` and how to use it to enforce data integrity.
*   **Tools:**
    *   Explain what a tool is, including its use in exposing capabilities to an agent that are not implicit in a base LLM.
    *   Show how to create and assign custom tools.
    *   Explain that type annotations and docstrings are used to provide context to agents about how to use each tool.
    *   Illustrate how to expose custom tooling via a function, and how to use the `marvin.tool` decorator.
    *   Note that Langchain tools are supported.
*   **Memory:**
    *   Explain how `Memory` objects store and recall information over time.
    *   Show how to configure different memory providers (including the default Chroma provider).
    *   Explain how instructions are used to tell agents when and how to interact with a memory module.
    *   Show how multiple memories can be passed to agents or tasks.
*   **Instructions**:
    *   Explain how instructions are used to specify the behavior of agents.
    *   Demonstrate how `marvin.instructions` can add ad-hoc or temporary instructions.
    *   Emphasize that these instructions are always included in the system prompt.
*   **Control Flow:**
    *   Explain how the orchestrator works by selecting tasks and passing them to agents for work.
    *   Describe the agentic loop and how to manage it, including max LLM calls, max agent turns, and early termination logic.
    *   Show how to implement manual iteration over a set of tasks with an orchestrator.
    *   Clearly explain `run_until` conditions for sophisticated control of task execution.
*   **Handlers:**
    * Explain how to use handlers to inspect and react to events emitted from a task.
    * Explain how to implement both sync and async handlers.
    * Show how to create custom handlers to perform a variety of different tasks.
    * Emphasize how to create a clear, testable, and maintainable event-driven architecture.
*   **Logging:**
    *   Clearly explain the global logging configuration and the behavior of Marvin's default print handler.
    *   Explain that all messages and tool calls can be logged (using the appropriate settings), but should not be relied upon in most production use cases.
    *   Emphasize that handlers should be used for capturing, processing, or storing information generated during a workflow.
*   **Batching and Parallelism:**
    *   Show how the use of list-based `result_type` can be used to batch process operations.
    *   Show how to use `asyncio.gather()` to execute tasks in parallel.
    *   Describe the differences and tradeoffs between the two approaches, and when each one should be used.
*   **Configuration:**
    *   Describe the available configuration options and how they can be accessed using the `settings` object.
    *   Explain that settings can be set at runtime, using environment variables, and using a `.env` file.
    *   Explain the available agent settings, model settings, and provider settings.

### 3. API Reference

*   **Comprehensive Documentation:** For each class, function, and method in the public API, generate reference-style documentation.
*   **Docstring Parsing:** Leverage the docstrings to automatically generate the base of API docs (using Sphinx or similar).
*   **Parameters and Returns:** Clearly document all parameters, their types, and default values. Also document the return type.
*   **Usage Examples:** Include specific code examples in each API doc that demonstrate how to use the item.
*   **Type Hints**: Be sure to include type hints in the API documentation to ensure users know what types to pass in and what types to expect.
*   **Specific Errors**: List common errors and exceptions that might be raised, and explain how to avoid them.

### 4. Examples

*   **Clear Objective:** Every example should have a clear purpose, demonstrating a specific feature or concept.
*   **Single Concept:** Prefer to demonstrate a single concept in isolation. When multiple concepts are shown, it should be because they are related to each other.
*   **Minimal Code:** Only include the minimum necessary code to demonstrate the topic. Avoid extraneous or unnecessary complexity.
*   **Realistic Scenario:** If possible, make the example a realistic and understandable use case of ControlFlow.
*   **Context:** Use clear and concise code comments, explaining what is happening in each line of code and why.

### 5. Style

*   **Code Highlighting:** Ensure code blocks have appropriate syntax highlighting by correctly specifying the language type (e.g. `python`).
*   **Callouts:** Prefer using callouts (e.g., `<Note>`, `<Tip>`, `<Warning>`) for important information.
*   **Tables:** Use tables to present tabular data or comparison effectively.
*   **Lists:** Use bulleted or numbered lists to break up content into easily digestible points.
*   **Code Group**: Whenever an example shows multiple snippets of code, use a `<CodeGroup>` tag to make them easily navigable.

## III. Specific Conventions

*   **Prefer context managers for threads:** Use the `with Thread() as thread:` syntax to specify which thread a task should run in. If you must pass around thread objects explicitly, do so by name and not by value.
*   **Favor type hints:** Include type hints on every function and method in code examples.
*   **Use meaningful variable names:** Avoid vague or single-letter variable names whenever possible.
*   **Add newlines**: Ensure there's always an empty line between code blocks, paragraphs, and other elements for easier reading.
*  **Use triple backticks**: Code blocks should use triple backticks with the language specified (e.g. ```python)
* **Check for empty blocks**: Do not include empty code or result blocks, which should be removed.

## IV. Tone and Audience

*   **Developer-Focused:** Marvin's documentation should be written for a developer audience that is comfortable with Python, though they may have little to no experience with LLMs.
*   **Empowering:** The goal is to empower developers with the knowledge and tools to build AI-powered applications easily.
*   **Pragmatic:** Focus on practical solutions and techniques, not on theoretical discussions.
*   **Clear and Confident:** The tone should be clear, direct, and confident in Marvin's capabilities.

## V. Ongoing Refinement

*   **Iterate:** Documentation should be continuously reviewed and improved based on feedback and code changes.
*   **Consistent Updates:** Ensure that all documentation is updated when APIs or core concepts are updated in the code.
*   **User Feedback:** Incorporate feedback from users to identify areas for improvement.

This guide will evolve as we build the documentation together. I'll refer to it frequently to ensure that all Marvin documentation adheres to its principles and requirements.
