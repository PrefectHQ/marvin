from typing import Any, Union

from marvin.types import CodeInterpreterTool, RetrievalTool, Tool

Retrieval = RetrievalTool()
CodeInterpreter = CodeInterpreterTool()

AssistantTool = Union[RetrievalTool, CodeInterpreterTool, Tool]


class CancelRun(Exception):
    """
    A special exception that can be raised in a tool to end the run immediately.
    """

    def __init__(self, data: Any = None):
        self.data = data
