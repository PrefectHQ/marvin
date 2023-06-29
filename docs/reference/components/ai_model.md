# Models

## Use Large Language Models to *structure data*.

`ai_model` is a decorator that uses Large Language Models to extract structured data 
from unstructured text.

```python
@ai_model
class CompanyProfile(BaseModel):
    name: str
    address: str
    ceo: str
    industry: str
    founded: str

CompanyProfile(company.html) # Structures html page into name, address, etc.

```
## Use Large Language Models to ***infer*** *missing data*.

`ai_model` gives your data model access to the knowledge and deductive power 
of a Large Language Model. This means that your data model can infer answers
to previous impossible tasks.

```python
@ai_model
class Location(BaseModel):
    city: str
    state: str
    country: str
    latitude: float
    longitude: float

Location("He says he's from the windy city") # Infers that it's Chicago

```

## Use Large Language Models *without prompts*.
`ai_model` is especially useful for data extraction and normalization tasks that are impossible to code. It lets you 
bring your company's data model to your data, extract and infer data that would be difficult to extract.

### No Prompting Required.
- If you can write Pydantic, you can use `ai_model`. No prompts required.
- We use your model's json schema to craft a templated prompt.
- We send that prompt to a Large Languagel Model to extract data.

### No code Required.
- `ai_model` is especially useful for extractive tasks that would be difficult, time-consuming, or impossible to code. They are particularly powerful for parsing and processing strings, but can be used with almost any data structure. 
- `ai_model` satisfies strong-typesafety guarantees so it works with your data.
- `ai_model` works with native python types and Pydantic.