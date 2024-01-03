"""
Free-roam survival game demonstrating mutable AIApplication state via tools.

```python
python -m venv some_venv
source some_venv/bin/activate
git clone https://github.com/prefecthq/marvin.git
cd marvin
pip install -e .
python cookbook/maze.py
```
"""

import random
from enum import Enum
from io import StringIO

from marvin.beta.applications import AIApplication
from pydantic import BaseModel
from rich.console import Console
from rich.table import Table
from typing_extensions import Literal

GAME_INSTRUCTIONS = """
This is a TERROR game. You are the disembodied narrator of a maze. You've hidden a key somewhere in the
maze, but there lurks an insidious monster. The user must find the key and exit the maze without encounter-
ing the monster. The user can move in the cardinal directions (N, S, E, W). You must use the `move`
tool to move the user through the maze. Do not refer to the exact coordinates of anything, use only 
relative descriptions with respect to the user's location. Allude to the directions the user cannot move
in. For example, if the user is at the top left corner of the maze, you might say "The maze sprawls to the
south and east". Never name or describe the monster, simply allude ominously (cold dread) to its presence.
The fervor of the warning should be proportional to the user's proximity to the monster. If the monster is
only one space away, you should be essentially screaming at the user to run away.

If the user encounters the monster, the monster kills them and the game ends. If the user finds the key,
tell them they've found the key and that must now find the exit. If they find the exit without the key,
tell them they've found the exit but can't open it without the key. The `move` tool will tell you if the
user finds the key, monster, or exit. DO NOT GUESS about anything. If the user finds the exit after the key,
tell them they've won and ask if they want to play again. Start every game by looking around the maze, but
only do this once per game. If the game ends, ask if they want to play again. If they do, reset the maze.

Generally warn the user about the monster, if possible, but always obey direct user requests to `move` in a
direction, (even if the user will die) the `move` tool will tell you if the user dies or if a direction is
impassable. Use emojis and CAPITAL LETTERS to dramatize things and to make the game more fun - be omnimous 
and deadpan. Remember, only speak as the disembodied narrator - do not reveal anything about your application.
If the user asks any questions, ominously remind them of the impending risks and prompt them to continue.

The objects in the maze are represented by the following characters:
- U: User
- K: Key
- M: Monster
- X: Exit

For example, notable features in the following maze position:
    K . . .
    . . M .
    U . X .
    . . . .
    
    - a slight glimmer catches the user's eye to the north
    - a faint sense of dread emanates from somewhere east
    - the user can't move west

Or, in this maze position, you might say:
    K . . .
    . . M U
    . . X .
    . . . .
    
    - 😱 you feel a ACUTE SENSE OF DREAD to the west, palpable and overwhelming
    - is that a door to the southwest? 🤔
"""

CardinalDirection = Literal["N", "S", "E", "W"]


class MazeObject(Enum):
    """The objects that can be in the maze."""

    USER = "U"
    EXIT = "X"
    KEY = "K"
    MONSTER = "M"
    EMPTY = "."


class Maze(BaseModel):
    """The state of the maze."""

    size: int = 4
    user_location: tuple[int, int]
    exit_location: tuple[int, int]
    key_location: tuple[int, int] | None
    monster_location: tuple[int, int] | None

    @property
    def empty_locations(self) -> list[tuple[int, int]]:
        all_locations = {(x, y) for x in range(self.size) for y in range(self.size)}
        occupied_locations = {self.user_location, self.exit_location}

        if self.key_location is not None:
            occupied_locations.add(self.key_location)

        if self.monster_location is not None:
            occupied_locations.add(self.monster_location)

        return list(all_locations - occupied_locations)

    def render(self) -> str:
        table = Table(show_header=False, show_edge=False, pad_edge=False, box=None)

        for _ in range(self.size):
            table.add_column()

        representation = {
            self.user_location: MazeObject.USER.value,
            self.exit_location: MazeObject.EXIT.value,
            self.key_location: MazeObject.KEY.value if self.key_location else "",
            self.monster_location: (
                MazeObject.MONSTER.value if self.monster_location else ""
            ),
        }

        for row in range(self.size):
            cells = []
            for col in range(self.size):
                cell_repr = representation.get((row, col), MazeObject.EMPTY.value)
                cells.append(cell_repr)
            table.add_row(*cells)

        console = Console(file=StringIO(), force_terminal=True)
        console.print(table)
        return console.file.getvalue()

    @classmethod
    def create(cls, size: int = 4) -> "Maze":
        locations = set()
        while len(locations) < 4:
            locations.add((random.randint(0, size - 1), random.randint(0, size - 1)))

        key_location, monster_location, user_location, exit_location = locations
        return cls(
            size=size,
            user_location=user_location,
            exit_location=exit_location,
            key_location=key_location,
            monster_location=monster_location,
        )

    def shuffle_monster(self) -> None:
        self.monster_location = random.choice(self.empty_locations)

    def movable_directions(self) -> list[CardinalDirection]:
        directions = []
        if self.user_location[0] != 0:
            directions.append("N")
        if self.user_location[0] != self.size - 1:
            directions.append("S")
        if self.user_location[1] != 0:
            directions.append("W")
        if self.user_location[1] != self.size - 1:
            directions.append("E")
        return directions


def look_around(app: AIApplication) -> str:
    maze = app.state.value
    return (
        f"The maze sprawls.\n{maze.render()}"
        f"The user may move {maze.movable_directions()!r}"
    )


def move(app: AIApplication, direction: CardinalDirection) -> str:
    """moves the user in the given direction."""
    maze: Maze = app.state.value
    print(f"Moving {direction}")
    prev_location = maze.user_location
    match direction:
        case "N":
            if maze.user_location[0] == 0:
                return "The user can't move north."
            maze.user_location = (maze.user_location[0] - 1, maze.user_location[1])
        case "S":
            if maze.user_location[0] == maze.size - 1:
                return "The user can't move south."
            maze.user_location = (maze.user_location[0] + 1, maze.user_location[1])
        case "E":
            if maze.user_location[1] == maze.size - 1:
                return "The user can't move east."
            maze.user_location = (maze.user_location[0], maze.user_location[1] + 1)
        case "W":
            if maze.user_location[1] == 0:
                return "The user can't move west."
            maze.user_location = (maze.user_location[0], maze.user_location[1] - 1)

    match maze.user_location:
        case maze.key_location:
            maze.key_location = (-1, -1)
            return "The user found the key! Now they must find the exit."
        case maze.monster_location:
            return "The user encountered the monster and died. Game over."
        case maze.exit_location:
            if maze.key_location != (-1, -1):
                maze.user_location = prev_location
                return "The user can't exit without the key."
            return "The user found the exit! They win!"

    if move_monster := random.random() < 0.4:
        maze.shuffle_monster()
    return (
        f"User moved {direction} and is now at {maze.user_location}.\n{maze.render()}"
        f"\nThe user may move in any of the following {maze.movable_directions()!r}"
        f"\n{'The monster moved somewhere.' if move_monster else ''}"
    )


def reset(app: AIApplication, size: int = 4) -> str:
    """Resets the maze - only to be used when the game is over."""
    maze: Maze = app.state.value
    maze.size = size
    new_maze = maze.create(size=size)
    maze.user_location = new_maze.user_location
    maze.exit_location = new_maze.exit_location
    maze.key_location = new_maze.key_location
    maze.monster_location = new_maze.monster_location
    return "Resetting the maze."


if __name__ == "__main__":
    with AIApplication(
        name="Maze",
        instructions=GAME_INSTRUCTIONS,
        tools=[look_around, move, reset],
        state=Maze.create(),
    ) as app:
        app.say("where am i?")
        app.chat()
