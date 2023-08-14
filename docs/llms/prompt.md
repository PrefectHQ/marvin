## Creating Prompts
Marvin lets you define dynamic prompts using code, eliminating the need for cumbersome template management. With this approach, you can easily create reusable and modular prompts, streamlining the development process.

!!! example "Example"

    ```python 
    from typing import Optional
    from marvin.prompts.library import System, User, ChainOfThought


    class ExpertSystem(System):
        content: str = (
            "You are a world-class expert on {{topic}}. "
            "When asked questions about {{topic}}, you answer correctly."
        )
        topic: Optional[str]


    prompt = (
        ExpertSystem(topic="python")
        | User("Write a function to find the nth Fibonacci number.")
        | ChainOfThought()  # Tell the LLM to think step by step
    )

    # We can now call `dict` to get the formatted messages.
    prompt.dict()

    ```

    ??? success "Click to see output"
        ```
        [
            {
                'role': 'system',
                'content': 'You are a world-class expert on python. 
                            When asked questions about python, you 
                            answer correctly.'
            },
            {
                'role': 'user',
                'content': 'I need to know how to write a function to
                            find the nth Fibonacci number.'
            },
            {  'role': 'assistant', 
                'content': "Let's think step by step."
            }
        ]

        ```

## Templating Prompts

In many applications, templating is unavoidable. In these cases, Marvin's optional templating engine simplifies the process of sharing context across prompts to an unprecedented level. By passing native Python types or Pydantic objects into the rendering engine, you can seamlessly establish context for entire conversations. This feature enables effortless information flow and context continuity throughout the prompt interactions.

!!! example "Example"

    ```python 
    from typing import Optional
    from marvin.prompts.library import System, User, ChainOfThought


    class ExpertSystem(System):
        content: str = (
            "You are a world-class expert on {{topic}}. "
            "When asked questions about {{topic}}, you answer correctly."
        )
        topic: Optional[str]


    prompt = (
        ExpertSystem()
        | User(
            "I need to know how to write a function in {{topic}} to find the nth Fibonacci "
            "number."
        )
        | ChainOfThought()  # Tell the LLM to think step by step
    )
    # We can now call `dict` with keyword arguments to get the formatted messages.
    prompt.dict(topic="rust")

    ```

    ??? success "Click to see output"
        ```
        [
            {
                'role': 'system',
                'content': 'You are a world-class expert on rust. 
                            When asked questions about rust, you answer correctly.'
            },
            {
                'role': 'user',
                'content': 'I need to know how to write a function in 
                            rust to find the nth Fibonacci number.'
            },
            {
                'role': 'assistant', 
                'content': "Let's think step by step."
            }
        ]

        ```

### Example: ReAct

!!! example "Example"

    ```python 
    from marvin.prompts.library import System


    class ReActPattern(System):
        content = """
        You run in a loop of Thought, Action, PAUSE, Observation.
        At the end of the loop you output an Answer
        Use Thought to describe your thoughts about the question you have been asked.
        Use Action to run one of the actions available to you - then return PAUSE.
        Observation will be the result of running those actions.
        """
    ```

### Example: SQL

!!! example "Example"

    ```python 
    import pydantic
    from marvin.prompts.library import System


    class ColumnInfo(pydantic.BaseModel):
        name: str
        description: str


    class SQLTableDescription(System):
        content = """
        If you chose to, you may query a table whose schema is defined below:
        
        {% for column in columns %}
        - {{ column.name }}: {{ column.description }}
        {% endfor %}
        """

        columns: list[ColumnInfo] = pydantic.Field(
            ..., description="name, description pairs of SQL Schema"
        )


    UserQueryPrompt = SQLTableDescription(
        columns=[
            ColumnInfo(name="last_login", description="Date and time of user's last login"),
            ColumnInfo(
                name="date_created",
                description="Date and time when the user record was created",
            ),
            ColumnInfo(
                name="date_last_purchase",
                description="Date and time of user's last purchase",
            ),
        ]
    )

    print(UserQueryPrompt.read())

    ```

    ??? success "Click to see output"
        ```python
        If you chose to, you may query a table whose schema is defined below:

        - last_login: Date and time of user's last login
        - date_created: Date and time when the user record was created
        - date_last_purchase: Date and time of user's last purchase

        ```

## Executing Prompts

Marvin makes executing one-off `task` or `chain` patterns dead simple. 

#### Running a `task`

Once you have a prompt defined, fire it off with your chosen LLM asyncronously like so:

!!! example "Example"
    ```python
    from marvin.prompts.library import System, User, ChainOfThought
    from marvin.engine.language_models import chat_llm
    from typing import Optional


    class ExpertSystem(System):
        content: str = (
            "You are a world-class expert on {{topic}}. "
            "When asked questions about {{topic}}, you answer correctly. "
            "You only answer questions about {{topic}}. "
        )
        topic: Optional[str]


    class Tutor(System):
        content: str = (
            "When you give an answer, you modulate your response based on the "
            "inferred knowledge of the user. "
            "Your student's name is {{name}}. "
        )
        name: str = "not provided"


    model = chat_llm()

    response = await model(
        (
            ExpertSystem()
            | Tutor()
            | User(
                "I heard that there are types of geometries when the angles don't add up to"
                " 180?"
            )
            | ChainOfThought()
        ).render(topic="geometry", name="Adam")
    )

    print(response.content)
    ```

    ??? success "Click to see output"
        ```
        Yes, you are correct! In traditional Euclidean geometry, 
        the angles of a triangle always add up to 180 degrees. 
        However, there are indeed other types of geometries where 
        this is not the case. One such example is non-Euclidean 
        geometry, which includes hyperbolic and elliptic geometries. 
        In hyperbolic geometry, the angles of a triangle add up to 
        less than 180 degrees, while in elliptic geometry, the angles 
        add up to more than 180 degrees. These non-Euclidean 
        geometries have their own unique properties and are 
        studied in mathematics and physics.
        ```
