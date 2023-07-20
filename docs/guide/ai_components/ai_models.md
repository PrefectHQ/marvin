# AI Models

!!! tip "Features"

    🧱 Drop-in replacment for Pydantic models that can be instantiated from natural language

    🔗 Transform raw text into type-safe outputs

    🎉 Create with a single `@ai_model` decorator

!!! abstract "Use Cases"

    🏗️ Entity extraction

    🧪 Synthetic data generation
    
    ✅ Standardization
    
    🧩 Type-safety


AI models are Pydantic models that are defined locally and use AI to process their inputs at runtime. Like normal Pydantic models, AI models define a schema that data must comply with. Unlike normal Pydantic models, AI models can handle unstructured text and automatically convert it into structured, type-safe outputs without requiring any additional source code!

To create an AI model, decorate any Pydantic model with `@ai_model`.

```python hl_lines="4"
import pydantic
from marvin import ai_model

@ai_model
class Resume(pydantic.BaseModel):
    first_name: str
    last_name: str
    phone_number: str = pydantic.Field(None, description='dash-delimited phone number')
    email: str
```
You can now create structured `Resume` objects from raw text: 
```python
Resume('Ford Prefect • (555) 5124-5242 • ford@prefect.io')
```
This produces a Pydantic model that is exactly equivalent to:
```python
Resume(
  first_name='Ford',
  last_name='Prefect',
  phone_number='555-5124-5242',
  email='ford@prefect.io'
)
```
!!! tip
    AI models work best with GPT-4, but results are still very good with GPT-3.5.

## When to use AI Models

Because AI models integrate seamlessly with the Pydantic framework, they are a straightforward way to infuse AI capabilities into your data processing pipeline. Just define the Pydantic model with the fields you want to extract from the unstructured text and use it anywhere! However, even though they can feel like magic, it's crucial to understand that there are situations where you might prefer not to use AI models.

Modern LLMs are extraordinarily potent, particularly when dealing with natural language and concepts that are simple to express but challenging to encode algorithmically. However, because they don't actually execute code, computing precise results can be tricky. 

For example, asking an AI to summarize intricate legal language is akin to asking a human to do the same -- it's feasible they'll comprehend the right context, but you'll probably want to double-check with a legal expert. On the other hand, you wouldn't ask the legal expert to summarize a complex research paper, which is a perfectly natural thing to ask an AI. 

Therefore, while there are many suitable times to use AI models, they aren't always a great fit. AI models tend to excel at exactly the things that are hard to codify algorithmically. If you're performing simple data validation, use a normal Pydantic model. If you're extracting context from unstructured text, use an AI model.

## Basic usage

The `ai_model` decorator can be applied to any Pydantic model. For optimal results, the model should have a descriptive name, annotated fields, and a class docstring. The model does not need to have any pre-processing or post-processing methods written. However, advanced users can add these methods to influence the output.

When an `ai_model`-decorated class is instantiated with unstructured text, all available information is sent to the AI. The AI generates a predicted output that is parsed according to the model's schema and returned as an instance of the model.

```python hl_lines="4"
import pydantic
from marvin import ai_model

@ai_model
class Resume(pydantic.BaseModel):
    first_name: str
    last_name: str
    phone_number: str = pydantic.Field(None, description='dash-delimited phone number')
    email: str

Resume('Ford Prefect • (555) 5124-5242 • ford@prefect.io')
```
This produces a Pydantic model that is exactly equivalent to:
```python
Resume(
  first_name='Ford',
  last_name='Prefect',
  phone_number='555-5124-5242',
  email='ford@prefect.io'
)
```


## Advanced usage

In addition to basic text instantiation, you can customize the behavior of AI models in a few ways. 
### Model customization

To customize models for your entire application, use Marvin's global settings object. To customize the model for a specific AI Model, pass an appropriate Model configuration:

```python
from marvin import ai_model
from marvin.llms import chat_llm

@ai_model(model=chat_llm(temperature=0.2, model='gpt-3.5-turbo'))
class MyModel(BaseModel):
    ...
```

### Guidance instructions
You can supply instructions to guide the parsing behavior
```python
@ai_model(instructions="Translate the text to French")
class Translator(BaseModel):
    text: str

model = Translator("Hello")
assert model.text == "Bonjour"
```

### Entity extraction

Each AI Model has a `.extract()` method that implements similar behavior to instantiating it on text.

```python hl_lines="4"
import pydantic
from marvin import ai_model

@ai_model
class Resume(pydantic.BaseModel):
    first_name: str
    last_name: str
    phone_number: str = pydantic.Field(None, description='dash-delimited phone number')
    email: str

# create a new Resume object from text
Resume.extract('Ford Prefect • (555) 5124-5242 • ford@prefect.io')
```

### Data generation

AI Models also have a `.generate()` method which encourages them to hallucinate missing fields rather than attempt to infer them directly from text. This makes it easy to generate synthetic data that matches a schema. 


```python hl_lines="4"
import pydantic
from marvin import ai_model

@ai_model
class Resume(pydantic.BaseModel):
    first_name: str
    last_name: str
    phone_number: str = pydantic.Field(None, description='dash-delimited phone number')
    email: str

# generate a Resume object
Resume.generate()

# generate a Resume object with guidance
Resume.generate("UK phone number")

# generate a Resume object with some fields known
Resume.generate(email='marvin@prefect.io')
```