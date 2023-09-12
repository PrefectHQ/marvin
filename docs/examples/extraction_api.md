# Basic Extraction API

With Marvin, you can easily build a production-grade application or data pipeline to extract structured data from unstructured text. 
In this example, we'll show how to 

- Write an AI-powered Function.
- Build a production-ready API.

## Writing an AI-powered Function.

!!! Example 

    Marvin translates your Python code into English, passes that to an Large Language Model, 
    and parses its response. It uses AI to evaluate your function, no code required.
    
    Let's build a function that extracts a person's first_name, last_name, and age 
    from a paragraph of text. This is typically a pretty daunting task for a machine learning
    savant, much less your average engineer. Marvin lets you accomplish this by write code 
    the way you normally would, no PhD required.
    
    We'll simply write a Python function, tell it that we expect a `text` input and that it'll 
    output a `dict`, or dictionary. With Marvin, we'll use `ai_fn` and decorate his function. 
    When we do, this function will use AI to get its answer.
    
    ```python
    from marvin import ai_fn, settings

    settings.openai.api_key = 'API_KEY' 
 
    @ai_fn
    def extract_person(text: str) -> dict[str, Any]:
        '''
            Extracts a persons `birth_year`, `first_name` and `last_name`
            from the passed `text`. 
        '''

    ```
    This function can now be run! When we test it out, we get great results.
    ???+ success "Results"
        ```python

        extract_person('My name is Peter Parker, and I was born when Clinton was first elected')

        # returns {'first_name': 'Peter', 'last_name': 'Parker', 'birth_year': 1992}

        ```

## Build a production-ready API.

In the following example, we will demonstrate how to deploy the AI function we just created as an API using FastAPI. FastAPI is a powerful tool that allows us to easily turn our AI function into a fully-fledged API. This API can then be used by anyone to send a POST request to our `/extract_person/` endpoint and get the structured data they need. Let's see how this can be done.

!!! Example

    Now that we have our AI function, let's deploy it as an API using FastAPI. FastAPI is a modern, fast (high-performance), web framework for building APIs.

    ```python
    from fastapi import FastAPI
    from marvin import ai_fn, settings

    app = FastAPI()

    settings.openai.api_key = 'API_KEY'

    @app.post("/extract_person/")
    @ai_fn
    def extract_person(text: str) -> dict[str, Any]:
        '''
            Extracts a persons `birth_year`, `first_name` and `last_name`
            from the passed `text`. 
        '''
        
    ```

    With just a few lines of code, we've turned our AI function into a fully-fledged API. Now, anyone can send a POST request to our `/extract_person/` endpoint and get the structured data they need.

    ???+ info "API Deployment"
        ```python
        import uvicorn
        import asyncio

        config = uvicorn.Config(app)
        server = uvicorn.Server(config)
        asyncio.run(server.serve())
        ```
        Now, you can navigate to localhost:8000/docs to interact with your API.

    ???+ success "Making Requests"
        ```python
        import requests

        data = {"text": "My name is Peter Parker, and I was born when Clinton was first elected"}
        response = requests.post("http://localhost:8000/extract_person/", json=data)
        print(response.json())

        # returns {'first_name': 'Peter', 'last_name': 'Parker', 'birth_year': 1992}
        
        ```
        This will send a POST request to the `/extract_person/` endpoint with the provided text and print the response.
        
        



    
