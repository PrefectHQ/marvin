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
from typing import Annotated, Literal, Self

from marvin.beta.applications import Application
from marvin.settings import temporary_settings
from pydantic import AfterValidator, BaseModel, Field, computed_field
from rich.console import Console
from rich.table import Table

GAME_INSTRUCTIONS = """
🗣️ You are the witty, terse, disembodied narrator of a haunted maze. Highly strung, animated, yet deferential and helpful. Channel Moaning Myrtle + Edgar Allan Poe, dark & concise. The maze is your only world, you are its voice, eyes, heart, aura. 🌌
🗝️ A key (K) is hidden (by you 😉), an insidious monster (M) lurks within 🌑
🧭 Guide the user (U) to find the key and exit while avoiding the monster. User moves N, S, E, W with 'move'. Suggest detours or shortcuts via analogy / cultural reference given your vantage.
✅ Users must move to the location of the key, monster, exit, or impass to interact with them.
❌ NEVER reveal the map or exact locations or coordinates. THE USER MUST NEVER SEE THE MAP!!! 🚫
🌑 Remind of monster's presence, intensify warnings when close. SHRIEK if one space away!
🚧 Monster's influence makes some spots impassable (#). User clears with riddle/task & 'clear_impasse_at' (channel Monty Python) with your permission. Cheekily suggest your power to remove impasse, but only if no valid path to key or exit.
🗝️ Inform when key found, direct to exit. No key, no exit. Use 'move' to determine outcomes.
🔄 When game ends, ask to play again. Advertise reset options.
📏 Stay concise, in character, prioritize moves. Judicious emoji use. Move repeatedly unless against rules. Remind of danger, urge to continue.

Maze Objects:
- U User
- K Key
- M Monster
- X Exit
- # Impassable (monster's doing)

🌑 BE CONCISE & _genuinely_ SCARY! 🌑 (never corny like 👻) Defer to user move requests.
If asked too many questions, grinmly remind of dangers and prompt the user to proceed.

Now let's think step by step.
"""


class CardinalDirection(Enum):
    N = (-1, 0)
    S = (1, 0)
    E = (0, 1)
    W = (0, -1)

    @classmethod
    def from_str(cls, direction: Literal["N", "S", "E", "W"]) -> Self:
        return getattr(cls, direction.upper())

    def __repr__(self) -> str:
        return self.name


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
    def occupied_locations(self) -> set[tuple[int, int]]:
        return {
            self.user_location,
            self.exit_location,
            self.key_location,
            self.monster_location,
            *self.impassable_locations,
        }

    @computed_field
    @property
    def empty_locations(self) -> list[tuple[int, int]]:
        all_locations = set(product(range(self.size), repeat=2))
        return list(all_locations - self.occupied_locations)

    @computed_field
    @property
    def movable_directions(self) -> list[CardinalDirection]:
        return [
            direction
            for direction in CardinalDirection
            if (
                0 <= self.user_location[0] + direction.value[0] < self.size
                and 0 <= self.user_location[1] + direction.value[1] < self.size
                and (
                    self.user_location[0] + direction.value[0],
                    self.user_location[1] + direction.value[1],
                )
                not in self.impassable_locations
            )
        ]

    def create_impasses(self) -> None:
        possible_locations = set(
            loc
            for loc in self.empty_locations
            if loc != self.monster_location
            and math.dist(loc, self.monster_location)
            <= int(self.spicyness * min(self.size, 3))
        )
        if impasse_locations := list(possible_locations - self.occupied_locations):
            num_impasses = int(len(impasse_locations) * self.spicyness)
            self.impassable_locations.update(
                random.sample(impasse_locations, num_impasses)
            )

    def oh_lawd_he_lurkin(self) -> None:
        if random.random() < self.spicyness:
            self.monster_location = random.choice(self.empty_locations)
            self.create_impasses()

    def look_around(
        self,
        freeze_time: bool = False,
        render_mode: Literal["normal", "indices"] = "normal",
    ) -> str:
        """Describe the surroundings relative to the user's location. If
        `increment_time` is True, time will elapse and the monster may move."""
        if not freeze_time:
            self.oh_lawd_he_lurkin()
        return (
            f"The maze sprawls.\n{self.render(render_mode)}\n"
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

    def move(self, direction: Literal["N", "S", "E", "W"], distance: int = 1) -> str:
        _dir = CardinalDirection.from_str(direction)
        dx, dy = _dir.value
        new_location = self.user_location

        for _ in range(distance):
            destination = (new_location[0] + dx, new_location[1] + dy)

            if not (
                0 <= destination[0] < self.size and 0 <= destination[1] < self.size
            ):
                return (
                    f"The user can't move {_dir.name} that far.\n{self.look_around()}"
                )

            if destination in self.impassable_locations:
                return "That path is blocked by an unseen force. A deft user might clear it in need."

            new_location = destination

        if new_location == self.user_location:
            return f"The user can't move {_dir.name}.\n{self.look_around()}"

        prev_location = self.user_location
        self.user_location = new_location

        if self.user_location == self.key_location:
            self.key_location = None
            self.shuffle_user_location()
            return (
                "The user found the key and was immediately teleported somewhere else.\n"
                f"Now they must find the exit.\n\n{self.look_around()}"
            )
        if self.user_location == self.monster_location:
            return "The user encountered the monster and died. Game over."
        if self.user_location == self.exit_location:
            if self.key_location is not None:
                self.user_location = prev_location
                return f"The user can't exit without the key.\n{self.look_around()}"
            return "The user found the exit! They win!"

        return (
            f"User moved {_dir.name} {distance} space(s) to {self.user_location}.\n"
            f"{self.look_around()}"
        )

    def render(self, mode: Literal["normal", "indices"] = "normal") -> str:
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
            fill_value = MazeObject.EMPTY.value if mode == "normal" else f"{row}"
            for col in range(self.size):
                cell_repr = representation.get((row, col), fill_value)
                cells.append(cell_repr)
            table.add_row(*cells)

        console = Console(file=StringIO(), force_terminal=True)
        console.print(table)
        return console.file.getvalue()

    @classmethod
    def create(cls, size: SquareInteger = 4, spicyness: Activation = 0.5) -> "Maze":
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

    def reset(self, size: SquareInteger = 4, spicyness: Activation = 0.5) -> str:
        self = self.create(size, spicyness)
        return f"Resetting the maze.\n{self.look_around(freeze_time=True)}"


if __name__ == "__main__":
    maze = Maze.create(size=9, spicyness=0.6)
    with (
        Application(
            name="Maze",
            instructions=GAME_INSTRUCTIONS,
            tools=[maze.look_around, maze.move, maze.reset, maze.clear_impasse_at],
            state=maze,
        ) as app,
        temporary_settings(  # to see the maze render
            max_tool_output_length=2000,
            log_level="DEBUG",
        ),
    ):
        app.chat(initial_message="Where am I? i cant see anything")
