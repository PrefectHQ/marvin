# Enforcing AI formatting

One of the most important "unlocks" for using AIs alongside and within your code is working with native data structures. This can be challenging for two reasons: first, because LLMs naturally exchange information through unstructured text; and second, because modern LLMs are trained with conversational objectives, so they have a tendency to interject extra words like "Sure, here's the data you requested:". This makes extracting structured outputs difficult.

Marvin can be used to get AIs to respond in structured, parseable forms. There are two common ways to enable this functionality, depending on whether you're using AI functions or bots. With AI functions, provide a return type annotation. With bots, provide a `response_format` argument. 

Under the hood, Marvin is creating a `ResponseFormatter` object that can handle sending instructions to the AI, validating the response, and parsing the output. It can even take steps to fix invalid responses. Most users will never have to create `ResponseFormatters` by hand, as Marvin will usually "do the right thing" when a return annotation or `response_format` is provided. 

## Learn more
For more detail, see the [bots docs](../concepts/bots.md#formatting-responses).

## Examples

Examples are shown for both AI functions and bots.

### Returning a string

```python
@ai_fn
def my_fn() -> str:
    """This function will return a string"""
```
```python
Bot() # bots return strings by default
```

### Returning a list of dicts
```python
@ai_fn
def my_fn() -> list[dict]:
    pass
```
```python
Bot(response_format=list[dict])
```
### Pydantic models

```python
class MyOutput(pydantic.BaseModel):
    x: int
    y: list[dict]

@ai_fn
def my_fn() -> list[MyOutput]:
    """This function will return a list of MyOutput models"""
```
```python
Bot(response_format=MyOutput)
```

### JSON objects

Instead of using Python types, you can describe the shape of the output. If your description includes the word "json", it will be automatically parsed and validated; otherwise it will be returned as a string

For example, these will both return structured objects:
```python
@ai_fn
def my_fn() -> 'a JSON list of strings and ints':
    """This function will return list[str | int]"""
```
```python
Bot(response_format = 'a JSON list of strings and ints')
```

While these will return strings (that could be parsed with `json.loads()`). Note the absence of the word JSON, which is what hints to Marvin to add a JSON parser to the `ResponseFormatter`.

```python
@ai_fn
def my_fn() -> 'a list of strings and ints':
    """This function will return list[str | int]"""
```
```python
Bot(response_format = 'a list of strings and ints')
```