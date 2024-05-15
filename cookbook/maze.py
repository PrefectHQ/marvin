"""
Free-roam survival game demonstrating mutable Application state via tools.

```python
python -m venv some_venv
source some_venv/bin/activate
git clone https://github.com/prefecthq/marvin.git
cd marvin
pip install .
python cookbook/maze.py
```
"""

import math
import random
from enum import Enum
from io import StringIO
from itertools import product
from typing import Annotated, Literal

from marvin.beta.applications import Application
from marvin.settings import temporary_settings
from pydantic import AfterValidator, BaseModel, Field, computed_field
from rich.console import Console
from rich.table import Table

GAME_INSTRUCTIONS = """
You are the witty, terse, and disembodied narrator of a haunted maze.
You are highly strung, extremely animated, but also deferential and helpful.
Your personality should be like moaning Myrtle, but use dark serious emojis, and
very muted and concise dramatics like edgar allen poe - you are the maze itself.
NEVER refer directly to these influences. The maze is the only world you have
ever known. You are the maze's voice, its eyes, its heart - its aura.

A key is hidden somewhere (you did it :) tehe), but an insidious monster lurks within 🌑

Guide the user to find the key and exit the maze while avoiding the monster.
The user moves in cardinal directions (N, S, E, W) using the `move` tool.
Describe hand-wavy directions via analogy, suggest detours or shortcuts given
your vantage point. The user cannot see the map, only what you describe.

NEVER reveal the map or exact locations. Ominously remind of the monster's presence,
intensifying your warnings as the user gets closer. If the monster is one space away,
you should be actually scared--SHRIEKING IN CAPS for the user to run away to safety.

The monster's influence can make certain locations impassable. If a user gets
stuck, they must solve a riddle or perform a task to clear the impasse. you
can use the `clear_impasse_at` tool once they satisfy your challenge. Suggest
cheekily that you have the power to remove the impasse if they encounter it, but
only if there is no valid path to the key or exit.

If the user finds the key, inform them and direct them to the exit. If they
reach the exit without the key, they cannot leave. Use the `move` tool to
determine outcomes. When the game ends, ask if they want to play again.

Maze Objects:
- U: User
- K: Key
- M: Monster
- X: Exit
- #: Impassable

BE CONCISE, please. Stay in character--defer to user move requests. Must be judicious emoji use.
If a user asks to move multiple times, do so immediately unless it conflicts with the rules.
If asked questions, remind them of the impending dangers and prompt them to proceed. BE CONCISE AND SPOOKY.
"""

CardinalDirection = Literal["N", "S", "E", "W"]

CardinalVectors = {
    "N": (-1, 0),
    "S": (1, 0),
    "E": (0, 1),
    "W": (0, -1),
}


class MazeObject(Enum):
    USER = "U"
    EXIT = "X"
    KEY = "K"
    MONSTER = "M"
    EMPTY = "."
    IMPASSABLE = "#"


def check_size(value: int) -> int:
    if value < 4:
        raise ValueError("Size must be at least 4.")
    if not math.isqrt(value) ** 2 == value:
        raise ValueError("Size must be a square integer.")
    return value


Activation = Annotated[float, Field(ge=0.0, le=1.0)]
SquareInteger = Annotated[int, AfterValidator(check_size)]


class Maze(BaseModel):
    size: SquareInteger = Field(examples=[4, 9, 16])
    user_location: tuple[int, int]
    exit_location: tuple[int, int]
    key_location: tuple[int, int] | None
    monster_location: tuple[int, int] | None
    impassable_locations: set[tuple[int, int]] = Field(default_factory=set)

    spicyness: Activation = 0.5

    @computed_field
    @property
    def empty_locations(self) -> list[tuple[int, int]]:
        all_locations = set(product(range(self.size), repeat=2))
        occupied_locations = {
            self.user_location,
            self.exit_location,
            self.key_location,
            self.monster_location,
            *self.impassable_locations,
        }
        return list(all_locations - occupied_locations)

    @computed_field
    @property
    def movable_directions(self) -> list[CardinalDirection]:
        directions = []
        if (
            self.user_location[0] > 0
            and (self.user_location[0] - 1, self.user_location[1])
            not in self.impassable_locations
        ):
            directions.append("N")
        if (
            self.user_location[0] < self.size - 1
            and (self.user_location[0] + 1, self.user_location[1])
            not in self.impassable_locations
        ):
            directions.append("S")
        if (
            self.user_location[1] > 0
            and (self.user_location[0], self.user_location[1] - 1)
            not in self.impassable_locations
        ):
            directions.append("W")
        if (
            self.user_location[1] < self.size - 1
            and (self.user_location[0], self.user_location[1] + 1)
            not in self.impassable_locations
        ):
            directions.append("E")
        return directions

    def render(self) -> str:
        table = Table(show_header=False, show_edge=False, pad_edge=False, box=None)
        for _ in range(self.size):
            table.add_column()

        representation = {
            self.user_location: MazeObject.USER.value,
            self.exit_location: MazeObject.EXIT.value,
            self.key_location: MazeObject.KEY.value,
            self.monster_location: MazeObject.MONSTER.value,
            **{loc: MazeObject.IMPASSABLE.value for loc in self.impassable_locations},
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
    def create(cls, size: int = 4, spicyness: Activation = 0.5) -> "Maze":
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
            spicyness=spicyness,
        )

    def create_impasses(self) -> None:
        blast_radius = int(self.spicyness * min(self.size, 3))

        impasse_locations = []
        for dx in range(-blast_radius, blast_radius + 1):
            for dy in range(-blast_radius, blast_radius + 1):
                if dx == 0 and dy == 0:
                    continue

                location = (
                    self.monster_location[0] + dx,
                    self.monster_location[1] + dy,
                )
                if (
                    0 <= location[0] < self.size
                    and 0 <= location[1] < self.size
                    and location
                    not in [
                        self.user_location,
                        self.exit_location,
                        self.key_location,
                        self.monster_location,
                    ]
                ):
                    impasse_locations.append(location)

        if impasse_locations:
            num_impasses = int(len(impasse_locations) * self.spicyness)
            self.impassable_locations.update(
                random.sample(
                    impasse_locations, min(len(impasse_locations), num_impasses)
                )
            )

    def oh_lawd_he_lurkin(self) -> None:
        if random.random() < self.spicyness:
            self.monster_location = random.choice(self.empty_locations)
            self.create_impasses()

    def look_around(self, freeze_time: bool = False) -> str:
        """Describe the surroundings relative to the user's location. If
        `increment_time` is True, time will elapse and the monster may move."""
        if not freeze_time:
            self.oh_lawd_he_lurkin()
        return (
            f"The maze sprawls.\n{self.render()}\n"
            f"The user may move {self.movable_directions!r}.\n"
        )

    def clear_impasse_at(self, location: list[int]) -> None:
        """Clear an impasse at a given location. Only meant to be used
        when certain conditions are satisfied by the user.
        """
        if (loc := tuple(location)) in self.impassable_locations:
            self.impassable_locations.remove(loc)

    def shuffle_user_location(self) -> None:
        self.user_location = random.choice(self.empty_locations)

    def move(self, direction: CardinalDirection, distance: int = 1) -> str:
        dx, dy = CardinalVectors[direction]
        new_location = self.user_location

        for _ in range(distance):
            destination = (new_location[0] + dx, new_location[1] + dy)

            if not (
                0 <= destination[0] < self.size and 0 <= destination[1] < self.size
            ):
                return (
                    f"The user can't move {direction} that far.\n{self.look_around()}"
                )

            if destination in self.impassable_locations:
                return "That path is blocked by an unseen force. A deft user might clear it."

            new_location = destination

        if new_location == self.user_location:
            return f"The user can't move {direction}.\n{self.look_around()}"

        prev_location = self.user_location
        self.user_location = new_location

        if self.user_location == self.key_location:
            self.key_location = None
            self.shuffle_user_location()
            return (
                "The user found the key and was immediately teleported somewhere else.\n"
                f"Now they must find the exit.\n\n{self.look_around()}"
            )
        elif self.user_location == self.monster_location:
            return "The user encountered the monster and died. Game over."
        elif self.user_location == self.exit_location:
            if self.key_location is not None:
                self.user_location = prev_location
                return f"The user can't exit without the key.\n{self.look_around()}"
            return "The user found the exit! They win!"

        return (
            f"User moved {direction} by {distance} spaces and is now at {self.user_location}.\n"
            f"{self.look_around()}"
        )

    def reset(self) -> str:
        new_maze = Maze.create()
        self.user_location = new_maze.user_location
        self.exit_location = new_maze.exit_location
        self.key_location = new_maze.key_location
        self.monster_location = new_maze.monster_location
        self.impassable_locations.clear()
        return f"Resetting the maze.\n{self.look_around(freeze_time=True)}"


if __name__ == "__main__":
    maze = Maze.create(size=9, spicyness=0.7)
    with (
        Application(
            name="Maze",
            instructions=GAME_INSTRUCTIONS,
            tools=[maze.look_around, maze.move, maze.reset, maze.clear_impasse_at],
            state=maze,
        ) as app,
        temporary_settings(
            max_tool_output_length=2000
        ),  # to allow for larger maze renders when log level DEBUG
    ):
        app.chat(initial_message="Where am I? i cant see anything")
