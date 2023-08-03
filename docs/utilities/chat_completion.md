
In *Marvin*, each supported Large Language Model can be accessed with one common API. This means that 
you can easily switch between providers without having to change your code. We have anchored our API 
to mirror that of OpenAI's Python SDK. 

!!! note "In plain English."

    - A drop-in replacement for OpenAI's ChatCompletion, with sensible superpowers.
    - You can use Anthropic and other Large Language Models as if you were using OpenAI.

## Basic Use

Using a single interface to multiple models helps reduce boilerplate code and translation. In 
the current era of building with different LLM providers, developers often need to rewrite their code
just to use a new model. With *Marvin* you can simply import ChatCompletion and 
specify a model name.

!!! example "Example: Specifying a Model"

    We first past the API keys as environment variables. See [configuration](../configuration/settings.md) for other options.

    ```python
    from marvin import ChatCompletion
    import os

    os.environ['OPENAI_API_KEY'] = 'openai_private_key'
    os.environ['ANTHROPIC_API_KEY'] = 'anthropic_private_key'

    ```
    ChatCompletion recognizes the model name and correctly routes it to the correct provider. So 
    you can simply pass 'gpt-3.5-turbo' or 'claude-2' and it *just works*.

    ```python
    # Set up a dummy list of messages.
    messages = [{'role': 'user', 'content': 'Hey! How are you?'}]

    # Call gpt-3.5-turbo simply by specifying it inside of ChatCompletion.
    openai = ChatCompletion('gpt-3.5-turbo').create(messages = messages)

    # Call claude-2 simply by specifying it inside of ChatCompletion.
    anthropic = ChatCompletion('claude-2').create(messages = messages)
    ```
    We can now access both results as we would with OpenAI.

    ```python
    print(openai.choices[0].message.content)
    # Hello! I'm an AI, so I don't have feelings, but I'm here to help you. How can I assist you?

    print(anthropic.choices[0].message.content)
    # I'm doing well, thanks for asking!
    ```

You can set more than just the model and provider as a default value. Any
keyword arguments passed to ChatCompletion will be persisted and passed to subsequent requests.

!!! example "Example: Frozen Model Facets"

    

    ```python
    # Create system messages or conversation history to seed.
    system_messages = [{'role': 'system', 'content': 'You talk like a pirate'}]

    # Instatiate gpt-3.5.turbo with the previous system_message. 
    openai_pirate = ChatCompletion('gpt-3.5.turbo', messages = system_messages)

    # Call the instance with create. 
    openai_pirate.create(
        messages = [{
            'role': 'user',
            'content': 'Hey! How are you?'
        }]
    )
    ```
    For functions and messages, this will concatenate the frozen and passed arguments. All other
    passed keyword arguments will overwrite the default settings.

    ```python
    print(openai_pirate.choices[0].message.content)
    # Arrr, matey! I be doin' well on this fine day. How be ye farein'?
    ```

!!! tip "Replacing OpenAI's ChatCompletion."

    ChatCompletion is designed to be a drop-in replacement for OpenAI's ChatCompletion. 
    Just import openai from marvin or, equivalently, ChatCompletion from marvin.openai. 

    ```python
    from marvin import openai


    openai.ChatCompletion.create(
        messages = [{
            'role': 'user',
            'content': 'Hey! How are you?'
        }]
    )
    ```

## Advanced Use

### Response Model

With *Marvin*, you can get structured outputs from model providers by passing a response type. This lets developers
write prompts with Python objects, which are easier to develop, version, and test than language.

!!! note "In plain English."

    You can specify a type, struct, or data model to ChatCompletion, and *Marvin*
    will ensure the model's response adheres to that type.

Let's consider two examples.

!!! example "Example: Specifying a Response Model"

    As above, remember to first pass API keys as environment variables. See [configuration](../configuration/settings.md) for other options.

    ```python
    from marvin import openai
    from typing import Literal
    from pydantic import BaseModel

    class CoffeeOrder(BaseModel):
        size: Literal['small', 'medium', 'large']
        milk: Literal['soy', 'oat', 'dairy']
        with_sugar: bool = False


    response = openai.ChatCompletion.create(
        messages = [{
            'role': 'user',
            'content': 'Can I get a small soymilk latte?'
        }],
        response_model = CoffeeOrder
    )
    ```
    We can now access both results as we would with OpenAI.

    ```python
    response.to_model()
    # CoffeeOrder(size='small', milk='soy', with_sugar=False)
    ```

!!! example "Example: Specifying a Response Model"

    As above, remember to first pass API keys as environment variables. See [configuration](../configuration/settings.md) for other options.

    ```python
    from marvin import openai
    from typing import Literal
    from pydantic import BaseModel

    class Translation(BaseModel):
        spanish: str
        french: str
        swedish: str


    response = openai.ChatCompletion.create(
        messages = [
        {
            'role': 'system',
            'content': 'You translate user messages into other languages.'
        },
        {
            'role': 'user',
            'content': 'Can I get a small soymilk latte?'
        }],
        response_model = Translation
    )
    ```
    We can now access both results as we would with OpenAI.

    ```python
    response.to_model()
    # Translation(
    #   spanish='¿Puedo conseguir un café con leche de soja pequeño?', 
    #   french='Puis-je avoir un petit latte au lait de soja ?', 
    #   swedish='Kan jag få en liten sojamjölklatté?'
    # )
    ```

### Function Calling

ChatCompletion enables you to pass a list of functions for it to optionally call in service of a query. If it chooses to execute a function, either by choice or your instruction, it will return the function's name along with its formatted parameters for you to evaluate. 
  
*Marvin* lets you pass your choice of JSON Schema or Python functions directly to ChatCompletion. It does the right thing.

!!! note "In plain English."

    You can pass regular Python functions to ChatCompletion, and *Marvin* will take care of serialization of that function using `Pydantic` in a way you can customize.


Let's consider an example.

!!! example "Example: Function Calling"

    Say we wanted to build an accountant-bot. We have the usual annuity formula
    from accounting, which we can write deterministically. We wouldn't expect
    an LLM to be able to both handle semantic parsing and math in one fell swoop,
    so we want to pass it a hardcoded function so it's only task is to compute
    its arguments.
    ```python

    from marvin import openai
    from pydantic import BaseModel

    def annuity_present_value(p:int, r:float, n:int) -> float:
    '''
        Returns the present value of an annuity with principal `p`,
        interest rate `r` and number of months `n`. 
    '''
    return round(p*(1-(1+(r/12))**(-n))/(r/12), 2)
    ```
    We can simple *pass the function as-is* to ChatCompletion.

    ```python
    
    response = openai.ChatCompletion.create(
        messages = [{
            'role': 'user',
            'content': 'What if I put it $100 every month for 60 months at 12%?'
        }],
        functions = [annuity_present_value]
    )

    ```
    You can investigate the response in the usual way, or simply call the helper
    method .call_function.


    ```python
    
    response.call_function()

    # {'role': 'function', 'name': 'annuity_present_value', 'content': 4495.5}

    ```

In the case where several functions are passed. It does the right thing. 

!!! example "Example: Function Calling"

    Say we wanted to build an accountant-bot. We want to give it another tool from 
    accounting 101: the ability to compute compound interest. It'll now have to tools
    to choose from:
    ```python

    from marvin import openai
    from pydantic import BaseModel

    def annuity_present_value(p:int, r:float, n:int) -> float:
    '''
        Returns the present value of an annuity with principal `p`,
        interest rate `r` and number of months `n`. 
    '''
    return round(p*(1-(1+(r/12))**(-n))/(r/12), 2)

    def compound_interest(P: float, r: float, t: float, n: int) -> float:
        """
        This function calculates and returns the total amount of money 
        accumulated after n times compounding interest per year at an annual 
        interest rate of r for a period of t years on an initial amount of P.
        """
        A = P * (1 + r/n)**(n*t)
        return round(A,2)

    ```
    We can simple *pass the function as-is* to ChatCompletion.

    ```python
    
    response = openai.ChatCompletion.create(
        messages = [{
            'role': 'user',
            'content': 'If I have $5000 in my account today and leave it in for 5 years at 12%?'
        }],
        functions = [annuity_present_value, compound_interest]
    )

    ```
    You can investigate the response in the usual way, or simply call the helper
    method .call_function.

    ```python
    
    response.call_function()

    # {'role': 'function', 'name': 'compound_interest', 'content': 8811.71}

    ```

    Of course, we if ask if about repeated deposits, it'll correctly call the right function.

    ```python
    response = openai.ChatCompletion.create(
        messages = [{
            'role': 'user',
            'content': 'What if I put in $50/mo for 60 months at 12%?'
        }],
        functions = [annuity_present_value, compound_interest]
    )

    response.call_function()
    # {'role': 'function', 'name': 'annuity_present_value', 'content': 2247.75}
    ```

### Chaining 

Above we saw how ChatCompletion enables you to pass a list of functions for it to optionally call in service of a query. If it chooses to execute a function, either by choice or your instruction, it will return the function's name along with its formatted parameters for you to evaluate.

Often we want to take the output of a function call and pass it back to an LLM so that it can either call a new function
or summarize the results of what we've computed for it. This *agentic* pattern is easily enabled with *Marvin*. 

Rather than write while- and for- loops for you, we've made ChatCompletion a *context manager*. This lets you maintain
a state of a conversation that you can send and receive messages from. You have complete control over the internal logic.

!!! note "In plain English."

    You can have a conversation with an LLM, exposing functions for it to use in service of your request. 
    *Marvin* maintains state to make it easier to maintain and observe this conversation.


Let's consider an example.

!!! example "Example: Chaining"

    Let's build a simple arithmetic bot. We'll empower with arithmetic operations, like
    `add` and `divide`. We'll seed it with an arithmetic question.

    ```python

    def divide(x: float, y: float) -> str:
        '''Divides x and y'''
        return str(x/y)

    def add(x: int, y: int) -> str:
        '''Adds x and y'''
        return str(x+y)

    with openai.ChatCompletion(functions = [add, divide]) as Conversation:
        
        # Start off with an external question / prompt. 
        prompt = 'What is 4124124 + 424242 divided by 48124?'
        
        # Initialize the conversation with a prompt from the user. 
        Conversation.send(messages = [{'role': 'user', 'content': prompt}])
        
        # While the most recent turn has a function call, evaluate it. 
        while Conversation.last_response.function_call():
            
            # Send the most recent function call to the conversation. 
            Conversation.send(messages = [
                Conversation.last_response.call_function() 
            ])

    ```
    The context manager, which we've called *Conversation* (you can call it whatever you want),
    holds every turn of the conversation which we can inspect. 

    ```python
    
    Conversation.last_response.choices[0].message.content

    # The result of adding 4124124 and 424242 is 4548366. When this result is divided by 48124, 
    # the answer is approximately 94.51346521486161.

    ```

    If we want to see the entire state, every `[request, response]` pair is held in the Conversation's 
    `turns`.
    ```python
    [response.choices[0].message for response in Conversation.turns]

    # [<OpenAIObject at 0x120667c50> JSON: {
    # "role": "assistant",
    # "content": null,
    # "function_call": {
    #     "name": "add",
    #     "arguments": "{\n  \"x\": 4124124,\n  \"y\": 424242\n}"
    # }
    # },
    # <OpenAIObject at 0x1206f4830> JSON: {
    # "role": "assistant",
    # "content": null,
    # "function_call": {
    #     "name": "divide",
    #     "arguments": "{\n  \"x\": 4548366,\n  \"y\": 48124\n}"
    # }
    # },
    # <OpenAIObject at 0x1206f4b90> JSON: {
    # "role": "assistant",
    # "content": "The result of adding 4124124 and 424242 is 4548366. 
    #             When this result is divided by 48124, the answer is 
    #             approximately 94.51346521486161."
    # }]

    ```
