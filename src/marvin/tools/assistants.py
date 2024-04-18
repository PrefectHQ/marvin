from typing import Any, Union

from marvin.types import CodeInterpreterTool, FileSearchTool, Tool

FileSearch = FileSearchTool()
CodeInterpreter = CodeInterpreterTool()

AssistantTool = Union[FileSearchTool, CodeInterpreterTool, Tool]

ENDRUN_TOKEN = "<|ENDRUN|>"


class EndRun(Exception):
    """
    A special exception that can be raised in a tool to end the run immediately.
    """

    def __init__(self, data: Any = None):
        self.data = data
