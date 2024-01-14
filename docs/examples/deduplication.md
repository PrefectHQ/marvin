# Entity Deduplication

???+ "How many distinct cities are there in the following text?"
    ```text
    windy city from illnois, The Windy City, New York City, the Big Apple, SF, San Fran, San Francisco,
    ```

    We can look and see the answer is 3, but how can we arrive here programmatically?

In this section, we'll explore using `marvin` to extract entities so we can use them directly in normal Python code.

## Creating our entity
To extract and deduplicate entities, we'll need to create an entity, i.e. the thing we are looking for.

In this case, we're looking for cities, so we'll create a `City` entity.

```python
from pydantic import BaseModel

class City(BaseModel):
    informal_name: str
    standard_name: str
    state: str | None = None
    country: str | None = None
```

We want to keep its raw name (`informal_name`) and its official name (`standard_name`), as well as its state and country, if applicable.

## Extracting entities
Now we can use `marvin.extract` to get a `list[City]` from our text.

```python
import marvin
from pydantic import BaseModel

class City(BaseModel):
    informal_name: str
    standard_name: str
    state: str | None = None
    country: str | None = None

cities = marvin.extract(
    "windy city from illnois, The Windy City, New York City, the Big Apple, SF, San Fran, San Francisco",
    City,
    instructions="Be sure to identify the origin country of the city if possible.",
)

print(
    set(total_entities := [city.standard_name for city in cities]),
    f" | {len(total_entities)=}"
)

print(
    "\n"+"\n".join(
        city.model_dump_json(indent=2)
        for city in cities
    )
)
```
??? Question "Click for the output"

    === "Output"
        ```python
        {'San Francisco', 'New York', 'Chicago'}  | len(total_entities)=7

        {
            "informal_name": "Windy City",
            "standard_name": "Chicago",
            "state": "Illinois",
            "country": "United States"
        }
        {
            "informal_name": "The Windy City",
            "standard_name": "Chicago",
            "state": "Illinois",
            "country": "United States"
        }
        {
            "informal_name": "New York City",
            "standard_name": "New York",
            "state": "New York",
            "country": "United States"
        }
        {
            "informal_name": "The Big Apple",
            "standard_name": "New York",
            "state": "New York",
            "country": "United States"
        }
        {
            "informal_name": "SF",
            "standard_name": "San Francisco",
            "state": "California",
            "country": "United States"
        }
        {
            "informal_name": "San Fran",
            "standard_name": "San Francisco",
            "state": "California",
            "country": "United States"
        }
        {
            "informal_name": "San Francisco",
            "standard_name": "San Francisco",
            "state": "California",
            "country": "United States"
        }
        ```