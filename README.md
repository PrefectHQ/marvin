<p align="center">
  <img src="docs/assets/images/heroes/it_hates_me_hero.png" style="width: 95%; height: auto;"/>
</p>

[![PyPI version](https://badge.fury.io/py/marvin.svg)](https://badge.fury.io/py/marvin)
[![Docs](https://img.shields.io/badge/docs-askmarvin.ai-blue)](https://www.askmarvin.ai)
[![Twitter Follow](https://img.shields.io/twitter/follow/AskMarvinAI?style=social)](https://twitter.com/AskMarvinAI)
[![Gurubase](https://img.shields.io/badge/Gurubase-Ask%20Marvin%20Guru-006BFF)](https://gurubase.io/g/marvin)

# Marvin

### The AI engineering toolkit

Marvin is a lightweight AI toolkit for building natural language interfaces that are reliable, scalable, and easy to trust.

Each of Marvin's tools is simple and self-documenting, using AI to solve common but complex challenges like entity extraction, classification, and generating synthetic data. Each tool is independent and incrementally adoptable, so you can use them on their own or in combination with any other library. Marvin is also multi-modal, supporting both image and audio generation as well as using images as inputs for extraction and classification.

Marvin is for developers who care more about _using_ AI than _building_ AI, and we are focused on creating an exceptional developer experience. Marvin users should feel empowered to bring tightly-scoped "AI magic" into any traditional software project with just a few extra lines of code.

Marvin aims to merge the best practices for building dependable, observable software with the best practices for building with generative AI into a single, easy-to-use library. It's a serious tool, but we hope you have fun with it.

Marvin is open-source, free to use, and made with 💙 by the team at [Prefect](https://www.prefect.io/).

## Installation

Install the latest version with `pip`:

```bash
pip install marvin -U
```

To verify your installation, run `marvin version` in your terminal.

## Tools

Marvin consists of a variety of useful tools, all designed to be used independently. Each one represents a common LLM use case, and packages that power into a simple, self-documenting interface.

### General

🦾 [Write custom AI-powered functions](https://askmarvin.ai/docs/text/functions) without source code

### Text

🏷️ [Classify text](https://askmarvin.ai/docs/text/classification) into categories

🔍 [Extract structured entities](https://askmarvin.ai/docs/text/extraction) from text

🪄 [Transform text](https://askmarvin.ai/docs/text/transformation) into structured data

✨ [Generate synthetic data](https://askmarvin.ai/docs/text/generation) from a schema

### Images

🖼️ [Create images](https://askmarvin.ai/docs/images/generation) from text or functions

📝 [Describe images](https://askmarvin.ai/docs/vision/captioning) with natural language

🏷️ [Classify images](https://askmarvin.ai/docs/vision/classification) into categories

🔍 [Extract structured entities](https://askmarvin.ai/docs/vision/extraction) from images

🪄 [Transform images](https://askmarvin.ai/docs/vision/transformation) into structured data

### Audio

💬 [Generate speech](https://askmarvin.ai/docs/audio/speech) from text or functions

✍️ [Transcribe speech](https://askmarvin.ai/docs/audio/transcription) from recorded audio

🎙️ [Record users](https://askmarvin.ai/docs/audio/recording) continuously or as individual phrases

### Video

🎙️ [Record video](https://askmarvin.ai/docs/video/recording) continuously

### Interaction

🤖 [Chat with assistants](https://askmarvin.ai/docs/interactive/assistants) and use custom tools

🧭 [Build applications](https://askmarvin.ai/docs/interactive/applications) that manage persistent state

# Quickstart

Here's a whirlwind tour of a few of Marvin's main features. For more information, [check the docs](https://askmarvin.ai/welcome/what_is_marvin/)!

## 🏷️ Classify text

Marvin can `classify` text using a set of labels:

```python
import marvin

marvin.classify(
    "Marvin is so easy to use!",
    labels=["positive", "negative"],
)

#  "positive"
```

Learn more about classification [here](https://askmarvin.ai/docs/text/classification).

## 🔍 Extract structured entities

Marvin can `extract` structured entities from text:

```python
import pydantic


class Location(pydantic.BaseModel):
    city: str
    state: str


marvin.extract("I moved from NY to CHI", target=Location)

# [
#     Location(city="New York", state="New York"),
#     Location(city="Chicago", state="Illinois")
# ]
```

Almost all Marvin functions can be given `instructions` for more control. Here we extract only monetary values:

```python
marvin.extract(
    "I paid $10 for 3 tacos and got a dollar and 25 cents back.",
    target=float,
    instructions="Only extract money"
)

#  [10.0, 1.25]
```

Learn more about entity extraction [here](https://askmarvin.ai/docs/text/extraction).


## ✨ Generate data

Marvin can `generate` synthetic data for you, following instructions and an optional schema:

```python
class Location(pydantic.BaseModel):
    city: str
    state: str


marvin.generate(
    n=4,
    target=Location,
    instructions="cities in the United States named after presidents"
)

# [
#     Location(city='Washington', state='District of Columbia'),
#     Location(city='Jackson', state='Mississippi'),
#     Location(city='Cleveland', state='Ohio'),
#     Location(city='Lincoln', state='Nebraska'),
# ]
```

Learn more about data generation [here](https://askmarvin.ai/docs/text/generation).

## 🪄 Standardize text by casting to types

Marvin can `cast` arbitrary text to any Python type:

```python
marvin.cast("one two three", list[int])

#  [1, 2, 3]
```

This is useful for standardizing text inputs or matching natural language to a schema:

```python
class Location(pydantic.BaseModel):
    city: str
    state: str


marvin.cast("The Big Apple", Location)

# Location(city="New York", state="New York")
```

For a class-based approach, Marvin's `@model` decorator can be applied to any Pydantic model to let it be instantiated from text:

```python
@marvin.model
class Location(pydantic.BaseModel):
    city: str
    state: str


Location("The Big Apple")

# Location(city="New York", state="New York")
```

Learn more about casting to types [here](https://askmarvin.ai/docs/text/transformation).

## 🦾 Build AI-powered functions

Marvin functions let you combine any inputs, instructions, and output types to create custom AI-powered behaviors... without source code. These functions can go well beyond the capabilities of `extract` or `classify`, and are ideal for complex natural language processing or mapping combinations of inputs to outputs.

```python
@marvin.fn
def sentiment(text: str) -> float:
    """
    Returns a sentiment score for `text`
    between -1 (negative) and 1 (positive).
    """

sentiment("I love working with Marvin!") # 0.8
sentiment("These examples could use some work...") # -0.2
```

Marvin functions look exactly like regular Python functions, except that you don't have to write any source code. When these functions are called, an AI interprets their description and inputs and generates the output.

Note that Marvin does NOT work by generating or executing source code, which would be unsafe for most use cases. Instead, it uses the LLM itself as a "runtime" to predict function outputs. That's actually the source of its power: Marvin functions can handle complex use cases that would be difficult or impossible to express as code.

You can learn more about functions [here](https://www.askmarvin.ai/docs/text/functions/).

## 🖼️ Generate images from text

Marvin can `paint` images from text:

```python
marvin.paint("a simple cup of coffee, still warm")
```

<p align="center">
  <img src="docs/assets/images/docs/images/coffee.png" style="width: 50%; height: auto;"/>
</p>

Learn more about image generation [here](https://askmarvin.ai/docs/images/generation).

## 🔍 Converting images to data

In addition to text, Marvin has support for captioning, classifying, transforming, and extracting entities from images using the GPT-4 vision model:

```python
marvin.classify(
    marvin.Image.from_path("docs/images/coffee.png"),
    labels=["drink", "food"],
)

# "drink"
```

## Record the user, modify the content, and play it back

Marvin can transcribe speech and generate audio out-of-the-box, but the optional `audio` extra provides utilities for recording and playing audio.

```python
import marvin
import marvin.audio

# record the user
user_audio = marvin.audio.record_phrase()

# transcribe the text
user_text = marvin.transcribe(user_audio)

# cast the language to a more formal style
ai_text = marvin.cast(user_text, instructions='Make the language ridiculously formal')

# generate AI speech
ai_audio = marvin.speak(ai_text)

# play the result
ai_audio.play()
```

# Get in touch!

💡 **Feature idea?** share it in the `#development` channel in [our Discord](https://discord.com/invite/Kgw4HpcuYG).

🐛 **Found a bug?** feel free to [open an issue](https://github.com/PrefectHQ/marvin/issues/new/choose).

👷 **Feedback?** Marvin is under active development, and we'd love to [hear it](https://github.com/PrefectHQ/marvin/discussions).
