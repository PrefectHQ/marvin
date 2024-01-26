# Generating synthetic data

Marvin can generate synthetic data according to a schema and instructions. Generating synthetic data with an LLM can yield extremely rich and realistic samples, making this an especially useful tool for testing code, training or evaluating models, or populating databases. 

<div class="admonition abstract">
  <p class="admonition-title">What it does</p>
  <p>
    The <code>generate</code> function creates synthetic data according to a specified schema and instructions. 
  </p>
</div>

!!! example
    
    === "Names (`str`)"

        We can generate a variety of names by providing instructions. Note the default behavior is to generate a list of strings:

        ```python
        import marvin

        names = marvin.generate(
            n=4, instructions="first names"
        )
        
        french_names = marvin.generate(
            n=4, instructions="first names from France"
        )
        
        star_wars_names = marvin.generate(
            n=4, instructions="first names from Star Wars"
        )
        
        ```

        !!! success "Result"
            
            ```python
            names == ['John', 'Emma', 'Michael', 'Sophia']

            french_names == ['Jean', 'Claire', 'Lucas', 'Emma']

            star_wars_names == ['Luke', 'Leia', 'Han', 'Anakin']
            ```

    === "Populations (`dict[str, int]`)"

        By providing a target type, we can generate dictionaries that map countries to their populations:
        
        ```python
        from pydantic import BaseModel

        populations = marvin.generate(
            target=dict[str, int],
            n=4, 
            instructions="a map of country: population",
        )
        ```

        !!! success "Result"
            
            ```python
            populations == [
                {'China': 1444216107},
                {'India': 1380004385},
                {'United States': 331893745},
                {'Indonesia': 276361783},
            ]
            ```
    === "Locations (Pydantic model)"

        Pydantic models can also be used as targets. Here's a list of US cities named for presidents:
        
        ```python
        from pydantic import BaseModel

        class Location(BaseModel):
            city: str
            state: str

        locations = marvin.generate(
            target=Location, 
            n=4, 
            instructions="cities in the United States named after presidents"
        )
        ```

        !!! success "Result"
            
            ```python
            locations == [
                Location(city='Washington', state='District of Columbia'),
                Location(city='Jackson', state='Mississippi'),
                Location(city='Cleveland', state='Ohio'),
                Location(city='Lincoln', state='Nebraska'),
            ]
            ```


<div class="admonition info">
  <p class="admonition-title">How it works</p>
  <p>
    Marvin instructs the LLM to generate a list of JSON objects that satisfy the provided schema and instructions. Care is taken to introduce variation in the output, so that the samples are not all identical.
  </p>
</div>

## Generating data

The `generate` function is the primary tool for generating synthetic data. It accepts a `type` argument, which can be any Python type, Pydantic model, or `Literal`. It also has an argument `n`, which specifies the number of samples to generate. Finally, it accepts an `instructions` argument, which is a natural language description of the desired output. The LLM will use these instructions, in addition to the provided type, to guide its generation process. Instructions are especially important for types that are not self documenting, such as Python builtins like `str` and `int`.


## Supported targets

`generate` supports almost all builtin Python types, plus Pydantic models, Python's `Literal`, and `TypedDict`. Pydantic models are especially useful for specifying specific features of the generated data, such as locations, dates, or more complex types. Builtin types are most useful in conjunction with instructions that provide more precise criteria for generation.

To specify the output type, pass it as the `target` argument to `generate`. The function will always return a list of `n` items of the specified type. If no target is provided, `generate` will return a list of strings.


!!! warning "Avoid tuples"
    OpenAI models currently have trouble parsing the API representation of tuples. Therefore we recommend using lists or Pydantic models (for more strict typing) instead. Tuple support will be added in a future release.

## Instructions

Data generation relies even more on instructions than other Marvin tools, as the potential for variation is much greater. Therefore, you should provide as much detail as possible in your instructions, in addition to any implicit documentation in your requested type. 

Instructions are freeform natural language and can be as general or specific as you like. The LLM will do its best to comply with any instructions you give.


## Model parameters
You can pass parameters to the underlying API via the `model_kwargs` argument of `generate`. These parameters are passed directly to the API, so you can use any supported parameter.

## Caching

Normally, each `generate` call would be independent. For some prompts, this would mean that each call produced very similar results to other calls. That would mean that generating, say, 10 items in a single call would produce a much more varied and high-quality result than generating 10 items in 5 calls of 2 items each.

To mediate this issue, Marvin maintains an in-memory cache of the last 100 results produced by each `generate` prompt. These responses are shown to the LLM during generation to encourage variation. Note that the cache is not persisted across Python sessions. Cached results are also subject to a token cap to avoid flooding the LLM's context window. The token cap can be set with `MARVIN_AI_TEXT_GENERATE_CACHE_TOKEN_CAP` and defaults to 600.

To disable this behavior, pass `use_cache=False` to `generate`.

Here is an example of how the cache improves generation. The first tab shows 10 cities generated in a single call; the second shows 10 cities generated in 5 calls of 2 cities each; and the third shows 10 cities generated in 5 calls but with the cache disabled.

The first and second tabs both show high-quality, varied results. The third tab is more disappointing, as it shows almost no variation.

=== "Single call"
    Generate 10 cities in a single call, which produces a varied list:

    ```python
    cities = marvin.generate(n=10, instructions='major US cities')
    ```

    !!! success "Result"
        ```python
        cities == [
            'New York',
            'Los Angeles',
            'Chicago',
            'Houston',
            'Phoenix',
            'Philadelphia',
            'San Antonio',
            'San Diego',
            'Dallas',
            'San Jose'
        ]
        ```

=== "Five calls, with caching"
    Generate 10 cities in a five calls, using the cache. This also produces a varied list:
    ```python
    cities = []
    for _ in range(5):
        cities.extend(marvin.generate(n=2, instructions='major US cities'))
    ```
    !!! success "Result"
        ```python
        cities == [
            'Chicago',
            'San Francisco',
            'Seattle',
            'New York City',
            'Los Angeles',
            'Houston',
            'Miami',
            'Dallas',
            'Atlanta',
            'Boston'
        ]
        ```
=== "Five calls, without caching"
    Generate 10 cities in five calls, without the cache. This produces a list with almost no variation, since each call is independent:
    
    ```python
    cities = []
    for _ in range(5):
        cities.extend(marvin.generate(
            n=2, 
            instructions='major US cities', 
            use_cache=False,
    ))
    ```
    !!! failure "Result"
        ```python
        cities == [
            'Houston',
            'Seattle',
            'Chicago',
            'Houston',
            'Chicago',
            'Houston',
            'Chicago',
            'Houston',
            'Los Angeles',
            'Houston'
        ]
        ```

## Async support
If you are using Marvin in an async environment, you can use `generate_async`:
  
```python
cat_names = await marvin.generate_async(
    n=4, 
    instructions="names for cats inspired by Chance the Rapper"
)

# ['Chancey', 'Rappurr', 'Lyric', 'Chano']
```