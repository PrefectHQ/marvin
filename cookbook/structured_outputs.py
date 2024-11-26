# /// script
# dependencies = ["marvin"]
# ///

from typing import Annotated

import marvin
from pydantic import AfterValidator, Field

result = marvin.extract(
    data="nO, i HaVe NeVeR HeaRd oF uV",
    target=Annotated[
        str,
        Field(description="letters, only vowels"),
        AfterValidator(lambda x: x.upper()),
    ],
)

assert isinstance(result, list)
assert set(sorted(result)) == {"A", "E", "I", "O", "U"}
