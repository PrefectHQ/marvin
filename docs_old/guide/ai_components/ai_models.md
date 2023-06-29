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

With Marvin, you use Pydantic to shape your data model as usual and enhance your model with `@ai_model`. This decorator imparts an extraordinary capability to your Pydantic model: the capability to manage unstructured text.

```python hl_lines="5"
from marvin import ai_model
import pydantic
from typing import Optional

@ai_model
class Resume(pydantic.BaseModel):
    first_name: str
    last_name: str
    phone_number: Optional[str]
    email: str

Resume('Ford Prefect • (555) 5124-5242 • ford@prefect.io').json(indent = 2)

#{
#     first_name: 'Ford',
#     last_name: 'Prefect',
#     email: 'ford@prefect.io',
#     phone: '(555) 5124-5242',
#}
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

```python hl_lines="5"
from marvin import ai_model
import pydantic
from typing import Optional

@ai_model
class Resume(pydantic.BaseModel):
	first_name: str
	last_name: str
	phone_number: Optional[str]
	email: str

Resume('Ford Prefect • (555) 5124-5242 • ford@prefect.io').json(indent = 2)

#{
# first_name: 'Ford',
# last_name: 'Prefect',
# email: 'ford@prefect.io',
# phone: '(555) 5124-5242',
# }
```


## Advanced usage

Under the hood, AI Models use AI Functions to extract data before it's passed to Pydantic's
validation rules. Unsurprisingly then, AI Models expose the same advanced customizations that AI Functions do. 

```python
@ai_model(llm_model='gpt-3.5-turbo', llm_temperature=0.2)
class MyFirstModel(pydantic.BaseModel):
    ...
```

You can customize the LLM's temperature, or give your AI Model access to Wikipedia, 
internal documentation, or a sanitized executable environment by using Marvin's [plugins](plugins.md). AI models have no plugins available by default in order to minimize the possibility of confusing behavior. See [AI function docs](ai_functions.md). 
