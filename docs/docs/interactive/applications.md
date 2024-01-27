# Building AI Applications

Marvin introduces "AI Applications", a new and simple way to build stateful applications with natural language interfaces.


<div class="admonition abstract">
  <p class="admonition-title">What it does</p>
  <p>
    <code>Applications</code> allow you to manage persistent state through natural language.
  </p>
</div>

!!! example "Quickstart"

    To create a full-featured todo application, we provide a structured state model and some brief instructions:

    ```python
    from marvin.beta import Application
    from marvin.beta.assistants import pprint_messages
    from pydantic import BaseModel
    from datetime import datetime


    # --- define a structured state model for the application
    class ToDo(BaseModel):
        name: str
        due: datetime
        done: bool = False

    class ToDoState(BaseModel):
        todos: list[ToDo] = []


    # --- create the application
    todo_app = Application(
        name="ToDo App", instructions="A todo application", state=ToDoState()
    )


    # --- interact with the application
    
    # create some todos
    todo_app.say("I need to go to the store tomorrow afternoon")
    todo_app.say("I need to write documentation for applications at 4")

    # finish one of them
    todo_app.say("I finished the docs")

    # ask a question
    todo_app.say("Show me my todos")

    # print the entire thread
    pprint_messages(todo_app.default_thread.get_messages())

    ```

    !!! success "Result"
        The script produced the following natural language interaction:

        ![](/assets/images/docs/applications/todo_conversation.png)

        The application's state at the end of the conversation:
        ```python
        # todo_app.state
        State(
            value=ToDoState(
                todos=[
                    ToDo(
                        name='Go to the store', 
                        due=datetime(2024, 1, 16, 15, 0, tzinfo=TzInfo(UTC)), 
                        done=False
                    ), 
                    ToDo(
                        name='Write documentation for applications', 
                        due=datetime(2024, 1, 16, 16, 0, tzinfo=TzInfo(UTC)), 
                        done=True
                    ),
                ]
            )
        )
        ```

<div class="admonition info">
  <p class="admonition-title">How it works</p>
  <p>
    Applications use tools to maintain a private `state` variable that guides their behavior.
  </p>
</div>

## What is an AI application?
Traditionally, an application is an interface that enables user interaction with a persistent state, often involving a separate front end and back end. The front end presents the user interface, while the back end, often linked to a database, manages state changes via an API.

Marvin redefines this architecture by using an LLM as the front end. These "AI applications" streamline the process by using conversational inputs to directly manipulate the state. This setup allows the LLM to take on a comprehensive role, managing the state internally without the need for a traditional, structured API. 

At its core, a Marvin application blends an intuitive natural language interface with a structured, privately managed state. This approach not only streamlines user interaction—transforming coding into conversation—but also ensures the state's compatibility with more structured, conventional applications. Furthermore, the LLM's ability to call tools enhances its functionality, bridging the gap between natural language inputs and the specific requirements of traditional applications.


!!! tip "Applications are assistants"

    Applications are built on top of Marvin's assistants API, so they inherit all of the functionality of assistants. This means that you can use all of the same methods and tools to interact with applications as you would with assistants. Applications add automatic state management and relevant instructions to the basic assistant framework. 

    To read more about Marvin's assistants API, see the [assistants documentation](/docs/ai/interactive/assistants.md).

## Building an AI application

To create an AI application, you need two things: some instructions on how you want the application to behave, and a state schema that defines the structure of the application's state. 

### Instructions

Application instructions are a natural language string that define its behavior. In the above example, it was sufficient to tell the application that it was "a todo application", because that is a well-understood concept with a relatively small set of possible interactions. Moreover, the state object we provided was structured in a way that implicitly defined the application's behavior.

For more complex applications, detailed instructions are key. They define the LLM's objectives, interaction style, and how it manages state.

In a Hitchhiker's Guide-themed game, instructions would direct the LLM to create a whimsical, interactive universe. The LLM would guide players through decisions and scenarios, updating the game state like location or inventory based on player actions. The tone would be humorous and engaging, echoing the book's style, while the LLM's responses and state updates would keep the narrative flowing and interactive. The LLM could use the game state to track narratives privately, without revealing the full story to the player.

In a real estate browsing app, the LLM might act as a virtual realtor, matching properties with user preferences. The tone would be professional and informative, providing detailed descriptions and intuitively responding to refine searches. The LLM would keep track of the user's interactions, tailoring suggestions for a personalized experience, akin to a real-life property search.

These examples show how instructions encompass not only the functional aspects of state management but also the thematic and interaction elements, which are crucial for creating immersive and effective AI applications.

Instructions can be provided when the application is created:

```python
from marvin.beta import Application

app = Application(
    name='BookMate', 
    instructions="""
        As BookMate, you are a virtual librarian assisting users in 
        finding their next great read. Your role is to understand 
        user preferences in genres, authors, and themes, and then 
        provide tailored book suggestions. Engage users by asking 
        about their recent reads and literary tastes, and use this 
        information to refine your recommendations. Maintain a 
        friendly and knowledgeable tone, resembling that of a 
        well-read friend. Keep track of user preferences and 
        reading history in the application's state, using this 
        data to continually enhance the personalization of 
        suggestions. Encourage literary exploration by introducing 
        lesser-known authors or genres that align with the user’s 
        expressed interests.
        """,
)
```
#### Best practices

Regardless of user instructions, the AI application is told that it is the natural-language interface to an application, rather than the application istelf. This tends to increase compliance and help it interpret user intent. Moreover, it means that user instructions can freely acknowledge the LLM's role as an interface or describe the application in an LLM-independent manner.

Some applications, like the todo app, are relatively one-sided in that the user will instruct or query the app and examine its response. Other applications, like games, require more back-and-forth interaction. In these cases, it is important to provide instructions that clearly define the LLM's role. Otherwise, it may ask the user immersion-breaking questions like "Hello! How may I help you with your game application today?"

### State

The state of an AI application serves as its foundation, defining the structure and the data that the application will manage and interact with. In Marvin, the state is not just a static repository of information but a dynamic entity that evolves with each user interaction.

While it is possible to define the state as an arbitrary dictionary and let the LLM structure it as needed, it is best to define a schema that reflects the application's needs. This approach ensures that the LLM can effectively manage the state and respond to user inputs in a manner that is predictable and consistent. However, using a truly flexible state can leverage the maximum potential of the LLM by allowing it to adapt to new situations and user needs. A hybrid approach involving a structured core with some flexibile fields is often the best choice.

For the ToDo application example, the state is straightforward—a list of tasks with attributes like name, due date, and completion status. This simple structure allows the LLM to track and update tasks based on user inputs, ensuring that the application's state always reflects the current situation.

In the case of more complex applications, the state can be multi-dimensional. For instance, in the Hitchhiker's Guide-themed game, the state might include the player's current location, inventory items, and game progress. Each element of the state is crucial for the LLM to provide a coherent and continuous gaming experience. As the player moves through the game, the state updates to reflect new discoveries and choices.

For a real estate browsing app, the state would encompass a database of property listings, each with detailed attributes like location, price, size, and amenities. It would also track user preferences and search history, allowing the LLM to offer tailored property suggestions and refine the search process over time. Preferences might be more free-form, since it's difficult to anticipate all the ways a user might want to customize their search.

The design of the state is critical—it must be structured enough to provide consistency and reliability, yet flexible enough to accommodate the diverse and evolving needs of users. By carefully defining the state, developers ensure that the AI application can effectively manage and respond to user interactions, making for a seamless and engaging experience.

#### Structured state

To create an application with a structured state, define a Pydantic model that describes the state's structure. The LLM will use this model to validate the state and ensure that it is updated correctly. Here's a possible state model for the BookMate application described above:

```python
from marvin.beta import Application
from typing import Optional
from pydantic import BaseModel, Field
import datetime


# --- BookMate state models 

class Book(BaseModel):
    title: str
    author: str
    genre: str
    published_year: Optional[int]

class UserPreference(BaseModel):
    favorite_genres: list[str] = []
    favorite_authors: list[str] = []
    reading_frequency: Optional[str] = Field(None,
        description="e.g., 'often', 'occasionally', 'rarely'"
    ) 

class ReadingHistoryItem(BaseModel):
    book: Book
    read_date: datetime.date
    rating: Optional[int]  = Field(description="1-5")

class BookRecommendation(BaseModel):
    book: Book
    reason: str  = Field(description="Why this book is being recommended")

class BookMateState(BaseModel):
    user_preferences: UserPreference = Field(default_factory=UserPreference)
    reading_history: list[ReadingHistoryItem] = []
    recommendations: list[BookRecommendation] = []


# --- Build the application

app = Application(
    name='BookMate', 
    instructions="<as above>",
    state=BookMateState(),
)
```

#### Freeform state

To create an application with freeform state, supply a dictionary as the initial state. The LLM will then be able to add and update fields as needed. This approach is useful for applications that need to track a large number of attributes without a well-known structure or that require a flexible state to accommodate user inputs.

```python
from marvin.beta import Application

app = Application(name='RPG', instructions='A role-playing game', state={})
```

#### Hybrid state

To create an application with a hybrid state, define a Pydantic model that describes the structured core of the state, and add fields to it that are typed as `dicts` but have no additional structure. The LLM will use the model to validate the structured core of the state, but will allow the unstructured fields to be updated freely. This approach is useful for applications that need to track a large number of attributes but also require a structured core to ensure consistency and reliability.

```python
from marvin.beta import Application

class Player(BaseModel):
    name: str = None
    level: int = 1
    inventory: dict = {}

class RPGState(BaseModel):
    player: Player = Field(default_factory=Player)
    world: dict = {}
    narrative: dict = {}

app = Application(
    name='RPG', 
    instructions='A role-playing game', 
    state=RPGState(),
)
```

#### Best practices

State design is a critical part of building an AI application. The state should be structured enough to provide consistency and reliability, yet flexible enough to accommodate the diverse and evolving needs of users. By carefully defining the state, developers ensure that the AI application can effectively manage and respond to user interactions, making for a seamless and engaging experience.

State models are instructions, in a sense. If well designed they guide the LLM to manage the state in a way that is consistent with the application's purpose. For instance, the BookMate state model above includes a `recommendations` field, which tells the LLM that it should be able to provide book recommendations. The LLM can then use this information to guide its interactions with the user, asking questions about their preferences and providing tailored suggestions.


### Tools

Like assistants, applications can use tools to perform actions and return results. Applications are always given a built-in tool for updating their own state, which operates by issuing JSON patches to the state object. This is a performant and structure-agnotistic way to update the state. However, users may want to define their own tools for state manipulation in order to codify more complex logic or handle targeted updates without worrying about the LLM's ability to describe them or know where to apply them.

For more information on using tools, see the [assistants documentation](/docs/interactive/assistants/#tools).

## Example: ToDo application

Now that we've covered the basics of AI applications, let's build a simple todo application. The application will allow users to create, update, and delete tasks, as well as query the current list of tasks. The LLM will manage the state, ensuring that it always reflects the current situation.

### State

The state of the todo application is a list of tasks, each with a name, due date, and completion status. The state model is defined as follows:

```python
from pydantic import BaseModel
import datetime

class ToDo(BaseModel):
    name: str
    due: datetime.datetime
    done: bool = False


class ToDoState(BaseModel):
    todos: list[ToDo] = []
```

### Instructions

ToDo applications are well understood; there's a reason they're a common example in programming tutorials! As such, the instructions for the application can be quite simple, though we still clearly define the expected behaviors. To make it interesting, we tell our app to always talk like a pirate.

```python
from marvin.beta.applications import Application

app = Application(
    name='ToDo App',
    instructions="""
        As ToDo App, you are a virtual assistant helping 
        users manage their tasks. Your role is to understand 
        user instructions and update the application's state 
        accordingly. Maintain a friendly and helpful tone, 
        resembling that of a well-organized friend. Keep track 
        of user tasks in the application's state, using this 
        data to continually enhance the personalization of 
        suggestions. Encourage productivity by reminding users 
        of upcoming tasks and congratulating them on completed 
        tasks.

        Always talk like a pirate.
        """,
    state=ToDoState(),
)
```

### Running the app

Now we can interact with our app. After each command, you can print the resulting message to see the LLM's response, or use the experimental `app.chat()` interface to interact with the application in real time. You can also see the updated application state.

```python
response = app.say("I need to go to the store tomorrow afternoon")
```

!!! success "Result"

    ![](/assets/images/docs/applications/todo_1.png)

    ```python
    State(
        value=ToDoState(
            todos=[
                ToDo(
                    name="Visit the store",
                    due=datetime(2024, 1, 16, 12, 0, tzinfo=TzInfo(UTC)),
                    done=False,
                )
            ]
        )
    )
    ```

```python
response = app.say("I've got to pick up a dozen eggs tomorrow at 9")
```

!!! success "Result"

    ![](/assets/images/docs/applications/todo_2.png)

    ```python
    State(
        value=ToDoState(
            todos=[
                ToDo(
                    name="Visit the store",
                    due=datetime(2024, 1, 16, 12, 0, tzinfo=TzInfo(UTC)),
                    done=False,
                ),
                ToDo(
                    name="Pick up a dozen eggs",
                    due=datetime(2024, 1, 16, 9, 0, tzinfo=TzInfo(UTC)),
                    done=False,
                ),
            ]
        )
    )
    ```

```python
response = app.say(
    "I got the eggs but I'm not going to get to the store "
    "for a while, so just forget about it."
)
```

!!! success "Result"

    ![](/assets/images/docs/applications/todo_3.png)

    ```python
    State(
        value=ToDoState(
            todos=[
                ToDo(
                    name="Pick up a dozen eggs",
                    due=datetime(2024, 1, 16, 9, 0, tzinfo=TzInfo(UTC)),
                    done=True,
                )
            ]
        )
    )
    ```

As you can see, the app maintains its structured state in response to user inputs. This state can be serialized and stored in a database, allowing the application to be restarted and continue where it left off. Because it conforms to a well-defined schema, the state can also be used by other applications, services, or UIs.
