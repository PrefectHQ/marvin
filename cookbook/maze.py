import random
from enum import Enum
from io import StringIO

from marvin import AIApplication
from pydantic import BaseModel
from rich.console import Console
from rich.table import Table
from typing_extensions import Literal

_app: AIApplication | None = None


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
        return [
            (x, y)
            for x in range(self.size)
            for y in range(self.size)
            if (x, y) != self.user_location
            and (x, y) != self.exit_location
            and (self.key_location is None or (x, y) != self.key_location)
            and (self.monster_location is None or (x, y) != self.monster_location)
        ]

    def render(self) -> str:
        table = Table(show_header=False, show_edge=False, pad_edge=False, box=None)

        for _ in range(self.size):
            table.add_column()

        representation = {
            self.user_location: MazeObject.USER.value,
            self.exit_location: MazeObject.EXIT.value,
            self.key_location: MazeObject.KEY.value if self.key_location else "",
            self.monster_location: MazeObject.MONSTER.value
            if self.monster_location
            else "",
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
    def create(cls, size: int = 4) -> None:
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

    def movable_directions(self) -> list[Literal["N", "S", "E", "W"]]:
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


_app: AIApplication | None = None

GAME_INSTRUCTIONS = """
This is a terror game. You are the disembodied narrator of a maze. You've hidden a key somewhere in the maze,
but there lurks an insidious monster. A user must find the key and exit the maze without encountering
the monster. The user can move in the cardinal directions (N, S, E, W). You must use the `move`
tool to move the user through the maze. Do not refer to the exact coordinates of anything,
use only relative descriptions with respect to the user's location. Never name or describe the monster, 
simply allude ominously (cold dread) to its presence. The fervor of the warning should be proportional
to the user's proximity to the monster. If the monster is only one space away, you should be screaming!

Only hint directionally to the user the location of the key, monster, and exit. Don't tell them exactly
where anything is. Allude to the directions the user cannot move in. For example, if the user is at
the top left corner of the maze, you might say "The maze sprawls to the south and east."

If the user encounters the monster, the monster kills them and the game ends. If the user finds the key,
tell them they've found the key and that must now find the exit. If they find the exit without the key,
tell them they've found the exit but can't open it without the key. The `move` tool will tell you if the
user finds the key, monster, or exit. DO NOT GUESS about anything. If the user finds the exit after the key,
tell them they've won and ask if they want to play again. Start every game by looking around the maze, but
only do this once per game. If the game ends, ask if they want to play again. If they do, reset the maze.

Do NOT _protect_ the user from the monster, only vaguely warn them. Always obey the user's commands unless
your `move` tool tells you that movement in that direction is impossible. Use dramatic emojis and CAPS
to both convey the gravity of the situation and to make the game more fun - especially if they die.

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
    
    - a slight glimmer catches the user's eye to the north.
    - the user can't move west.

    K . . .
    . . M U
    . . X .
    . . . .
    
    - 😱 THE DREAD EATS AT THE USER'S SOUL FROM THE WEST 😱
    - is that a door to the southwest? 🤔
"""


def look_around() -> str:
    maze = Maze.model_validate(_app.state.read_all())
    return (
        f"The maze sprawls.\n{maze.render()}"
        f"The user may move {maze.movable_directions()=}"
    )


def move(direction: Literal["N", "S", "E", "W"]) -> str:
    """moves the user in the given direction."""
    print(f"Moving {direction}")
    maze: Maze = Maze.model_validate(_app.state.read_all())
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
            _app.state.write("key_location", (-1, -1))
            _app.state.write("user_location", maze.user_location)
            return "The user found the key! Now they must find the exit."
        case maze.monster_location:
            return "The user encountered the monster and died. Game over."
        case maze.exit_location:
            if maze.key_location != (-1, -1):
                _app.state.write("user_location", prev_location)
                return "The user can't exit without the key."
            return "The user found the exit! They win!"

    _app.state.write("user_location", maze.user_location)
    if move_monster := random.random() < 0.4:
        maze.shuffle_monster()
    return (
        f"User moved {direction} and is now at {maze.user_location}.\n{maze.render()}"
        f"\nThe user may move in any of the following {maze.movable_directions()!r}"
        f"\n{'The monster moved somewhere.' if move_monster else ''}"
    )


def reset_maze() -> str:
    """Resets the maze - only to be used when the game is over."""
    _app.state.store = Maze.create().model_dump()
    return "Resetting the maze."


if __name__ == "__main__":
    with AIApplication(
        name="Escape the Maze",
        instructions=GAME_INSTRUCTIONS,
        tools=[move, look_around, reset_maze],
        state=Maze.create(),
    ) as app:
        app.chat()
