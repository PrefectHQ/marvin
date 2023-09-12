"""
This module provides tools for file system operations such as reading and writing files.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field

from .._compat import field_validator, validate_arguments
from . import Tool


class FileSystemTool(Tool):
    """
    Base class for file system operations. It provides a root directory field and a
    method to validate paths.
    """

    root_dir: Optional[Path] = Field(
        None,
        description=(
            "Root directory for files. If provided, only files nested in or below this"
            " directory can be read. "
        ),
    )

    def validate_paths(self, paths: List[str]) -> Union[List[Path], List[str]]:
        """
        If `root_dir` is set, ensures that all paths are children of `root_dir`.
        """
        if self.root_dir:
            for path in paths:
                if ".." in path:
                    raise ValueError(f"Do not use `..` in paths. Got {path}")
                if not (self.root_dir / path).is_relative_to(self.root_dir):
                    raise ValueError(f"Path {path} is not relative to {self.root_dir}")
            return [self.root_dir / path for path in paths]
        return paths


class ListFiles(FileSystemTool):
    """
    Tool for listing all files at or optionally under a provided path.
    """

    description: str = """
        Lists all files at or optionally under a provided path. {%- if root_dir
        %} Paths must be relative to {{ root_dir }}. Provide '.' instead of '/'
        to read root. {%- endif %}}
        """

    root_dir: Optional[Path] = Field(
        None,
        description=(
            "Root directory for files. If provided, only files nested in or below this"
            " directory can be read."
        ),
    )

    def run(self, path: str, include_nested: bool = True) -> List[str]:  # type: ignore
        """List all files in `root_dir`, optionally including nested files."""
        [path] = self.validate_paths([path])  # type: ignore
        if include_nested:
            files = [str(p) for p in path.rglob("*") if p.is_file()]  # type: ignore
        else:
            files = [str(p) for p in path.glob("*") if p.is_file()]  # type: ignore

        # filter out certain files
        files = [
            file
            for file in files
            if not (
                "__pycache__" in file
                or "/.git/" in file
                or file.endswith("/.gitignore")
            )
        ]

        return files


class ReadFile(FileSystemTool):
    """
    Tool for reading the content of a specific file, optionally providing start
    and end rows.
    """

    description: str = """
    Read the content of a specific file, optionally providing start and end
    rows.{% if root_dir %} Paths must be relative to {{ root_dir }}. Provide '.'
    instead of '/' to read root.{%- endif %}}
    """

    def run(self, path: str, start_row: int = 1, end_row: int = -1) -> str:  # type: ignore # noqa: E501
        [path] = self.validate_paths([path])  # type: ignore
        with open(path, "r") as f:
            content = f.readlines()

        if start_row == 0:
            start_row = 1
        if start_row > 0:
            start_row -= 1
        if end_row < 0:
            end_row += 1

        if end_row == 0:
            content = content[start_row:]
        else:
            content = content[start_row:end_row]

        return "\n".join(content)


class ReadFiles(FileSystemTool):
    """
    Tool for reading the entire content of multiple files at once. Due to context size
    limitations, reading too many files at once may cause truncated responses.
    """

    description: str = """
    Read the entire content of multiple files at once. Due to context size
    limitations, reading too many files at once may cause truncated responses.
    {% if root_dir %} Paths must be relative to {{ root_dir }}. Provide '.'
    instead of '/' to read root.{%- endif %}}
    """

    def run(self, paths: List[str]) -> Dict[str, str]:  # type: ignore
        """Load content of each file into a dictionary of path: content."""
        content = {}
        for path in self.validate_paths(paths):
            with open(path) as f:
                content[path] = f.read()
        return content  # type: ignore


class WriteContent(BaseModel):
    """
    Model for writing content to a file. It includes the path, content, write mode,
    and the row to insert at.
    """

    path: str
    content: str
    write_mode: Literal["overwrite", "append", "insert"] = "append"
    insert_at_row: Optional[int] = None

    @field_validator("content")
    def content_must_be_string(cls, v: Any) -> str:
        if v and not isinstance(v, str):
            try:
                v = json.dumps(v)
            except json.JSONDecodeError:
                raise ValueError("Content must be a string or JSON-serializable.")
        return v

    # @field_validator
    # def check_insert_model(cls, values):
    #     if values["insert_at_row"] is None and values["write_mode"] == "insert":
    #         raise ValueError("Must provide `insert_at_row` when using `insert` mode.")
    #     return values


class WriteFile(FileSystemTool):
    """
    Tool for writing content to a file.
    """

    description: str = """
        Write content to a file.
        
        {%if root_dir %} Paths must be relative to {{ root_dir }}.{% endif %}}
        
        {%if require_confirmation %} You MUST ask the user to confirm writes by
        showing them details. {% endif %}
        """
    require_confirmation: bool = True

    def run(self, write_content: WriteContent) -> str:  # type: ignore
        [path] = self.validate_paths([write_content.path])

        # ensure the parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)  # type: ignore

        if write_content.write_mode == "overwrite":
            with open(path, "w") as f:
                f.write(write_content.content)
        elif write_content.write_mode == "append":
            with open(path, "a") as f:
                f.write(write_content.content)
        elif write_content.write_mode == "insert":
            with open(path, "r") as f:
                contents = f.readlines()
            contents[write_content.insert_at_row] = write_content.content  # type: ignore # noqa: E501

            with open(path, "w") as f:
                f.writelines(contents)

        return f"Files {write_content.path} written successfully."


class WriteFiles(WriteFile):
    """
    Tool for writing content to multiple files. Each `WriteContent` object in the
    `contents` argument is an instruction to write to a specific file.
    """

    description: str = """
        Write content to multiple files. Each `WriteContent` object in the
        `contents` argument is an instruction to write to a specific file.
        
        {%if root_dir %} Paths must be relative to {{ root_dir }}.{% endif %}}
        
        {%if require_confirmation %} You MUST ask the user to confirm writes by
        showing them details. {% endif %}
        """
    require_confirmation: bool = True

    @validate_arguments
    def run(self, contents: List[WriteContent]) -> str:  # type: ignore
        for wc in contents:
            super().run(write_content=wc)
        return f"Files {[c.path for c in contents]} written successfully."
