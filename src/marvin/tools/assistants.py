from typing import Any, Union

from marvin.requests import CodeInterpreterTool, FunctionTool, RetrievalTool, Tool

Retrieval = RetrievalTool()
CodeInterpreter = CodeInterpreterTool()

AssistantTools = list[Union[FunctionTool, RetrievalTool, CodeInterpreterTool, Tool]]


class EndRun(Exception):
    """
    A special exception that can be raised in a tool to end the run.
    """

    def __init__(self, data: Any = None):
        self.data = data
