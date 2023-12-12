from typing import Any, Union

from pydantic import BaseModel

from marvin.requests import CodeInterpreterTool, RetrievalTool, Tool

Retrieval = RetrievalTool[BaseModel]()
CodeInterpreter = CodeInterpreterTool[BaseModel]()

AssistantTools = Union[
    RetrievalTool[BaseModel], CodeInterpreterTool[BaseModel], Tool[BaseModel]
]


class CancelRun(Exception):
    """
    A special exception that can be raised in a tool to end the run immediately.
    """

    def __init__(self, data: Any = None):
        self.data = data
