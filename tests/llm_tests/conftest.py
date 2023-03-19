from pathlib import Path

import pytest


def pytest_collection_modifyitems(config, items):
    for item in items:
        # any files in this directory should be marked as an llm test
        try:
            if item.path.relative_to(Path(__file__).parent):
                item.add_marker(pytest.mark.llm)
        except ValueError:
            pass
