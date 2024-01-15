# Generating synthetic data

Marvin can generate synthetic data according to a schema and instructions. Generating synthetic data with an LLM can yield extremely rich and realistic samples, making this an especially useful tool for testing code, training or evaluating models, or populating databases. 

<div class="admonition abstract">
  <p class="admonition-title">What it does</p>
  <p>
    The <code>generate</code> function creates synthetic data according to a specified schema and instructions. 
  </p>
</div>

!!! example
    
    === "Names"

        We can generate a variety of names by providing instructions:

        ```python
        import marvin

        names = marvin.generate(
            str, n=4, instructions="first names"
        )
        
        french_names = marvin.generate(
            str, n=4, instructions="first names from France"
        )
        
        star_wars_names = marvin.generate(
            str, n=4, instructions="first names from Star Wars"
        )
        
        ```

        !!! success "Result"
            
            ```python
            assert names == ['John', 'Emma', 'Michael', 'Sophia']

            assert french_names == ['Jean', 'Claire', 'Lucas', 'Emma']

            assert star_wars_names == ['Luke', 'Leia', 'Han', 'Anakin']
            ```

    === "Locations"

        We can also generate structured data, such as locations:
        
        ```python
        from pydantic import BaseModel

        class Location(BaseModel):
            city: str
            state: str

        locations = marvin.generate(
            Location, 
            n=4, 
            instructions="cities in the United States named after famous people"
        )
        ```

        !!! success "Result"
            
            ```python
            assert locations == [
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


## Supported types

`generate` supports almost all builtin Python types, plus Pydantic models, Python's `Literal`, and `TypedDict`. Pydantic models are especially useful for specifying specific features of the generated data, such as locations, dates, or more complex types. Builtin types are most useful in conjunction with instructions that provide more precise criteria for generation.

Note that `generate` will always return a list of type you provide. 

## Instructions

Data generation relies even more on instructions than other Marvin tools, as the potential for variation is much greater. Therefore, you should provide as much detail as possible in your instructions, in addition to any implicit documentation in your requested type. 


