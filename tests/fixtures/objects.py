import marvin
import pytest


@pytest.fixture
def simple_bot():
    """
    A simple bot that responds in a matter-of-fact way with no plugins and no
    date in the prompt.

    Uses default instructions.
    """
    return marvin.Bot(
        personality="Keeps its answers direct and brief.",
        plugins=[],
        include_date_in_prompt=False,
    )
