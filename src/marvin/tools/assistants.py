from typing import Any, Union

from marvin.requests import CodeInterpreterTool, RetrievalTool, Tool

Retrieval = RetrievalTool()
CodeInterpreter = CodeInterpreterTool()

AssistantTools = list[Union[RetrievalTool, CodeInterpreterTool, Tool]]


class CancelRun(Exception):
    """
    A special exception that can be raised in a tool to end the run immediately.
    """

    def __init__(self, data: Any = None):
        self.data = data
