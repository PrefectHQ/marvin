# Basic Classifier API

With Marvin, you can easily build a production-grade application or data pipeline to classify data from unstructured text. 
In this example, we'll show how to 

- Write an AI-powered Function.
- Build a production-ready API.

## Writing an AI-powered Function.

!!! Example 

    Marvin translates your Python code into English, passes that to an Large Language Model, 
    and parses its response. It uses AI to evaluate your function, no code required.
    
    Let's build a function that classifies a paragraph of text into predefined categories. 
    This is typically a pretty daunting task for a machine learning savant, much less your average engineer. 
    Marvin lets you accomplish this by writing code the way you normally would, no PhD required.
    
    We'll simply write a Python function, tell it that we expect a `text` input and that it'll 
    output a `str`, or string. With Marvin, we'll use `ai_fn` and decorate this function. 
    When we do, this function will use AI to get its answer.
    
    ```python
    import marvin
    from typing import Literal

    marvin.settings.openai.api_key = 'API_KEY' 

    @marvin.fn
    def classify_text(text: str) -> Literal['sports', 'politics', 'technology']:
        '''
            Correctly classifies the passed `text` into one of the predefined categories. 
        '''

    ```
    This function can now be run! When we test it out, we get great results.
    ???+ success "Results"
        ```python

        classify_text('The Lakers won the game last night')

        # returns Category.SPORTS

        ```

## Build a production-ready API.

In the following example, we will demonstrate how to deploy the AI function we just created as an API using FastAPI. FastAPI is a powerful tool that allows us to easily turn our AI function into a fully-fledged API. This API can then be used by anyone to send a POST request to our `/classify_text/` endpoint and get the classified category they need. Let's see how this can be done.

!!! Example

    Now that we have our AI function, let's deploy it as an API using FastAPI. FastAPI is a modern, fast (high-performance), web framework for building APIs.

    ```python
    import marvin
    from fastapi import FastAPI
    from typing import Literal

    marvin.settings.openai.api_key = 'API_KEY' 

    app = FastAPI()

    @app.post("/classify_text/")
    @marvin.fn
    def classify_text(text: str) -> Literal['sports', 'politics', 'technology']:
        '''
            Correctly classifies the passed `text` into one of the predefined categories. 
        '''
    ```

    With just a few lines of code, we've turned our AI function into a fully-fledged API. Now, anyone can send a POST request to our `/classify_text/` endpoint and get the classified category they need.

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

        data = {"text": "The Lakers won the game last night"}
        response = requests.post("http://localhost:8000/classify_text/", json=data)
        print(response.json())

        # returns 'SPORTS'
        
        ```
        This will send a POST request to the `/classify_text/` endpoint with the provided text and print the response.
