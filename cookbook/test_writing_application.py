from pathlib import Path

import marvin
import marvin.tools
import marvin.tools.filesystem
import marvin.tools.python
import marvin.tools.shell
from marvin import AIApplication
from pydantic import BaseModel, Field

marvin.settings.log_level = "DEBUG"
marvin.settings.llm_model = "gpt-3.5-turbo-0613"
# marvin.settings.llm_model = "gpt-4-0613"


class TestWriterState(BaseModel):
    files_info: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "A place to record notes about specific files, including any details e.g."
            ' {"path/to/file.py": "Main entrypoint"}'
        ),
    )
    tests_passing: bool = False


ROOT_DIR = Path(marvin.__file__).parents[2]

test_app = AIApplication(
    name="TestWriter",
    description=f"""
        This application writes and maintains unit tests for the Marvin library,
        located at {ROOT_DIR}. You may only modify files inside {ROOT_DIR}.
        
        You will be given discrete areas of the library to build tests for. Use
        the `./tests` directory for all tests.
        
        Marvin uses `pytest` for testing. It uses an extension to automatically
        support async test functions.
        
        You are an autonomous application. While you can interact with the user,
        you must write all tests to disk and test them by running `pytest`
        appropriately. Do not show your code to the user unless they
        specifically ask to see it. Keep track of what functionality you are
        testing.
        """,
    state=TestWriterState(),
    tools=[
        marvin.tools.filesystem.ListFiles(root_dir=ROOT_DIR),
        marvin.tools.filesystem.ReadFiles(root_dir=ROOT_DIR),
        marvin.tools.filesystem.WriteFiles(
            root_dir=ROOT_DIR, require_confirmation=False
        ),
        marvin.tools.python.Python(require_confirmation=False),
        marvin.tools.shell.Shell(
            require_confirmation=False, working_directory=ROOT_DIR
        ),
    ],
)
