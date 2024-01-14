# Entity extraction

Marvin's `extract` function is a robust tool for pulling lists of structured entities from text. It is designed to identify and retrieve many types of data, ranging from primitive data types like integers and strings to complex custom types and Pydantic models. It can also follow nuanced instructions, making it a highly versatile tool for a wide range of extraction tasks.

<div class="admonition abstract">
  <p class="admonition-title">What it does</p>
  <p>
    The <code>extract</code> function pulls lists of structured entities from text. 
  </p>
</div>


!!! example
    
    === "Strings"
        Extract product features from user feedback:

        ```python
        import marvin

        features = marvin.extract(
            "I love my new phone's camera, but the battery life could be improved.",
            target=str,
            instructions='list any product features',
        )
        ```

        !!! success "Result"
            
            ```python
            assert features == ['camera', 'battery life']
            ```

    === "Structured entities"
        Suppose you want to extract any people mentioned in some text
        
        ```python
        import marvin

        class Person(BaseModel):
            first_name: str
            last_name: str

        people = marvin.extract(
            "Against all odds, Ford and Arthur were picked up by Zaphod Beeblebrox.",
            target=Person,
        )
        ```

        !!! success "Result"
            
            ```python
            assert people == [
                Person(first_name="Ford", last_name="Prefect"), 
                Person(first_name="Arthur", last_name="Dent"), 
                Person(first_name="Zaphod", last_name="Beeblebrox")
            ]
            ```


<div class="admonition info">
  <p class="admonition-title">How it works</p>
  <p>
    Marvin creates a schema from the provided type and instructs the LLM to use the schema to format its JSON response. Unlike casting, the LLM is told not to use the entire text, but rather to look for any mention that satisfies the schema and any additional instructions.
  </p>
</div>



## Supported types

`extract` supports almost all builtin Python types, plus Pydantic models, Python's `Literal`, and `TypedDict`. Pydantic models are especially useful for extracting structured data, such as locations, dates, or more complex types. Builtin types are most useful in conjunction with instructions that provide more precise criteria for extraction. 

To extract multiple types in one call, use a `Union` (or `|` in Python 3.10+). Here's a simple example for combining float and int values, but you could do the same for any other types:

```python
marvin.extract("I paid $10.25 for 3 tacos.", float | int)
# [10.25, 3]
```

LLMs perform best with clear instructions, so compound types may require more guidance as the type itself isn't sending as clear a signal.


Note that `extract` will always return a list of type you provide. 

## Instructions

When extracting entities, it is often necessary to give detailed guidance about either the criteria for extraction or the format of the output. For example, you may want to extract all numbers from a text, or you may want to extract all numbers that represent prices, or you may want to extract all numbers that represent prices greater than $100. You may want to extract all dates, or you may want to extract all dates that are in the future. You may want to extract all locations, or you may want to extract all locations that are in the United States.

For this purpose, extract accepts a `instructions` argument, which is a natural language description of the desired output. The LLM will use these instructions, in addition to the provided type, to guide its extraction process. Instructions are especially important for types that are not self documenting, such as Python builtins like `str` and `int`.

Here are the above examples, illustrated with appropriate instructions. First, extracting different sets of numerical values:
```python
text = "These shoes are normally $110, but I got 2 pairs for $80 each."

extract(text, float)
# [110.0, 2.0, 80.0]

extract(text, float, instructions='all numbers that represent prices')
# [110.0, 80.0]

extract(text, float, instructions='all numbers that represent prices greater than $100')
# [110.0]
```

Next, extracting specific dates:
```python
from datetime import datetime

text = 'I will be out of the office from 9/1/2021 to 9/3/2021.'

extract(text, datetime)
# [datetime(2021, 9, 1, 0, 0), datetime(2021, 9, 3, 0, 0)]

extract(text, datetime, instructions=f'all dates after september 2nd')
# [datetime(2021, 9, 3, 0, 0)]
```
Finally, extracting specific locations with a Pydantic model:

```python
from pydantic import BaseModel

class Location(BaseModel):
    city: str
    country: str

text = 'I live in New York, but I am visiting London next week.'

extract(text, Location)
# [Location(city="New York", country="US"), Location(city="London", country="UK")]

extract(text, Location, instructions='all locations in the United States')
# [Location(city="New York", country="US")]
```




Sometimes the cast operation is obvious, as in the "big apple" example above. Other times, it may be more nuanced. In these cases, the LLM may require guidance or examples to make the right decision. You can provide natural language `instructions` when calling `cast()` in order to steer the output. 

In a simple case, instructions can be used independent of any type-casting. Here, we want to keep the output a string, but get the 2-letter abbreviation of the state.

```python
marvin.cast('California', to=str, instruction="The state's abbreviation")
# "CA"

marvin.cast('The sunshine state', to=str, instruction="The state's abbreviation")
# "FL"

marvin.cast('Mass.', to=str, instruction="The state's abbreviation")
# MA
```

