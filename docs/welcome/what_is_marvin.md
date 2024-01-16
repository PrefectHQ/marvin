# What is Marvin?


Marvin is a lightweight AI toolkit for building natural language interfaces that are reliable, scalable, and easy to trust. 

Each of Marvin's tools is simple and self-documenting, using AI to solve common but complex challenges like entity extraction, classification, and generating synthetic data. Each tool is independent and incrementally adoptable, so you can use them on their own or in combination with any other library. Marvin is also multi-modal, supporting both image and audio generation as well using images as inputs for extraction and classification.

Marvin is for developers who care more about *using* AI than *building* AI, and we are focused on creating an exceptional developer experience. Marvin users should feel empowered to bring tightly-scoped "AI magic" into any traditional software project with just a few extra lines of code.

Marvin aims to merge the best practices for building dependable, observable software with the best practices for building with generative AI into a single, easy-to-use library. It's a serious tool, but we hope you have fun with it. 

Marvin is open-source, free to use, and made with 💙 by the team at [Prefect](https://www.prefect.io/).


!!! Example "What's it like to use Marvin?"

    === "Classify text"

        Classify any text against a set of labels:
    
        ```python
        import marvin

        result = marvin.classify(
            "Marvin is so easy to use!", 
            labels=["positive", "negative"],
        )
        ```

        !!! success "Result"
            ```python
            assert result == "positive"
            ```

    === "Extract entities"
    
        Extract product features from user feedback:

        ```python
        import marvin

        features = marvin.extract(
            "I love my new phone's camera, but the battery life could be improved.",
            instructions="product features",
        )
        ```

        !!! success "Result"
            
            ```python
            features == ['camera', 'battery life']
            ```

    === "Standardize inputs"
        Convert natural language to a structured form:

        ```python hl_lines="10"
        import marvin
        from pydantic import BaseModel, Field


        class Location(BaseModel):
            city: str
            state: str = Field(description='2-letter abbreviation')


        result = marvin.cast('the big apple', Location)
        ```

        !!! success "Result"
            ```python
            assert result == Location(city="New York", state="NY")
            ```

    
    === "Generate data"
        Generate synthetic data from a schema and instructions:

        ```python hl_lines="10-14"
        import marvin
        from pydantic import BaseModel, Field


        class Location(BaseModel):
            city: str
            state: str = Field(description='2-letter abbreviation')


        result = marvin.generate(
            n=4, 
            target=Location, 
            instructions='US cities named after presidents',
        )
        ```
    
        !!! success "Result"
            ```python
            result == [
                Location(city="Washington", state="DC"),
                Location(city="Jefferson City", state="MO"),
                Location(city="Lincoln", state="NE"),
                Location(city="Madison", state="WI"),
            ]
            ```

    === "Custom AI functions"

        Marvin functions let you combine any inputs, instructions, and output types to create custom AI-powered behaviors.

        ```python hl_lines="3"
        import marvin

        @marvin.fn
        def list_fruits(n: int, color: str) -> list[str]:
            """Generates a list of `n` fruits that are `color`"""

        fruits = list_fruits(3, color='red') 
        ```

        !!! success "Result"
            
            ```python
            fruits == ["apple", "cherry", "strawberry"]
            ```

        Note that `list_fruits` has no source code. Marvin's components turn your function into a prompt, ask AI for its most likely output, and parses its response.
        

??? Question "Explain Marvin like I'm 5"
    === "(I'm a technical 5-year-old)"

        Marvin lets your software speak English and ask questions to Large Language Models.

        It introspects the types and docstrings of your functions and data models, and automatically renders them as prompts for an LLM. You write code as you would normally, rather than prompts, and Marvin handles the back-and-forth translation. 

        This lets you focus on what you've always focused on: writing clean, versioned, reusable *code* and *data models*, and not scrutinizing whether you begged your LLM hard enough to output JSON or needed to offer it a bigger tip for the right answer.

        Extracting, generating, cleaning, or classifying data is as simple as writing a function or a data model.

    === "(I'm not technical)"

        Marvin lets engineers who know Python use Large Language Models without needing to write prompts.

        It turns out that ChatGPT and other Large Language Models are good at performing boring but incredibly valuable business-critical tasks beyond being a chatbot: you can use them to classify emails as spam, extract key figures from a report - exactly however you want for your scenario. When you use something like ChatGPT you spend a lot of time crafting the right prompt or context to get it to write your email, plan your date night, etc.
        
        If you want your software to use ChatGPT, you need to let it turn its objective into English. Marvin handles this 'translation' for you, so you get to just write code like you normally would. Engineers like using Marvin because it lets them write software like they're used to.
        
        Simply put, it lets you use Generative AI without feeling like you have to learn a framework.

