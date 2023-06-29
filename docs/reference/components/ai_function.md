
# Functions

## Use Large Language Models to *evaluate functions*.

`ai_fn` is a decorator that uses Large Language Models to evaluate Python functions. 

```python
@ai_fn
def extract_products(text: str) -> list[str]:
    """Returns a list of all products mentioned in a webpage"""
```

## Use Large Language Models *without prompts*.
`ai_fn` is especially useful for activies that would be difficult, time-consuming, or impossible to code. They are particularly powerful for parsing and processing strings, but can be used with almost any data structure. 

### No Prompting Required.
- If you can write python, you can use `ai_fn`. No prompts required.
- We use your function's name, docstring, and signature to craft a templated prompt.
- We send that prompt to a Large Languagel Model to infer its answer.

### No code Required.
- `ai_fn` is especially useful for activies that would be difficult, time-consuming, or impossible to code. They are particularly powerful for parsing and processing strings, but can be used with almost any data structure. 
- `ai_fn` satisfies strong-typesafety guarantees so it works with your data.
- `ai_fn` works with native python types and Pydantic.

### Write impossible code.
AI functions are especially useful for activies that would be difficult, time-consuming, or impossible to code. They are particularly powerful for parsing and processing strings, but can be used with almost any data structure. 

```python
@ai_fn
def extract_keywords(text:str, criteria:str=None) -> list[str]:
    """
    Extract important keywords from text, optionally only including 
    those that meet the provided criteria (for example, "colors", 
    "proper nouns", or "European capitals")
    """
```

## Use Large Language Models to *generate data*.

### General real fake data.
Use hallucination as a literal figurative feature. Use python or pydantic
to describe the data model you need, and generate realistic data on the fly 
for sales demos.

### Rapidly prototype natural language pipelines.
Use hallucination as a literal feature. Generate data that would be impossible
or prohibatively expensive to purchase as you rapidly protype NLP pipelines. 

```python
@ai_fn
def generate_synthetic_data(n: str, condition: str) -> list[Person]:
    """
    Generates `n` synthetic patient and symptom profiles 
    for `condition`.
    """
```
