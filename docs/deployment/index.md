
## FastAPI

We strongly recommend deploying Marvin's components with FastAPI. Here's how you can deploy a declarative API gateway in a few lines of code.


```
from fastapi import FastAPI
from marvin import ai_fn, ai_model
from pydantic import BaseModel
import uvicorn
import asyncio

app = FastAPI()


@ai_fn
def generate_fruits(n: int) -> list[str]:
    """Generates a list of `n` fruits"""


@ai_fn
def generate_vegetables(n: int, color: str) -> list[str]:
    """Generates a list of `n` vegetables of color `color`"""


@ai_model
class Person(BaseModel):
    first_name: str
    last_name: str


app.add_api_route("/generate_fruits", generate_fruits)
app.add_api_route("/generate_vegetables", generate_vegetables)
app.add_api_route("/person/extract", Person.route())
```

If you want to serve the previous example from, say, a Jupyter Notebook for local testing, you can also include:


```
# ... from above
# If you want to run an API from a Jupyter Notebook.

config = uvicorn.Config(app)
server = uvicorn.Server(config)
await server.serve()

# Then navigate to localhost:8000/docs
```
