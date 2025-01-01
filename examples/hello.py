from typing import Annotated

from marvin import generate
from pydantic import Field

Fruit = Annotated[str, Field(description="A fruit")]


if __name__ == "__main__":
    print(generate(Fruit, n=3, instructions="with high vitamin C content"))
