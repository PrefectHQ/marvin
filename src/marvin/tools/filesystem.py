import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, root_validator, validate_arguments, validator

from marvin.tools import Tool


class FileSystemTool(Tool):
    root_dir: Path = Field(
        None,
        description=(
            "Root directory for files. If provided, only files nested in or below this"
            " directory can be read. "
        ),
    )

    def validate_paths(self, paths: list[str]) -> list[Path]:
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
    description: str = """
        Lists all files at or optionally under a provided path. {%- if root_dir
        %} Paths must be relative to {{ root_dir }}. Provide '.' instead of '/'
        to read root. {%- endif %}}
        """

    root_dir: Path = Field(
        None,
        description=(
            "Root directory for files. If provided, only files nested in or below this"
            " directory can be read."
        ),
    )

    def run(self, path: str, include_nested: bool = True) -> list[str]:
        """List all files in `root_dir`, optionally including nested files."""
        [path] = self.validate_paths([path])
        if include_nested:
            files = [str(p) for p in path.rglob("*") if p.is_file()]
        else:
            files = [str(p) for p in path.glob("*") if p.is_file()]

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
    description: str = """
    Read the content of a specific file, optionally providing start and end
    rows.{% if root_dir %} Paths must be relative to {{ root_dir }}. Provide '.'
    instead of '/' to read root.{%- endif %}}
    """

    def run(self, path: str, start_row: int = 1, end_row: int = -1) -> str:
        [path] = self.validate_paths([path])
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
    description: str = """
    Read the entire content of multiple files at once. Due to context size
    limitations, reading too many files at once may cause truncated responses.
    {% if root_dir %} Paths must be relative to {{ root_dir }}. Provide '.'
    instead of '/' to read root.{%- endif %}}
    """

    def run(self, paths: list[str]) -> dict[str, str]:
        """Load content of each file into a dictionary of path: content."""
        content = {}
        for path in self.validate_paths(paths):
            with open(path) as f:
                content[path] = f.read()
        return content


class WriteContent(BaseModel):
    path: str
    content: str
    write_mode: Literal["overwrite", "append", "insert"] = "append"
    insert_at_row: int = None

    @validator("content", pre=True)
    def content_must_be_string(cls, v):
        if v and not isinstance(v, str):
            try:
                v = json.dumps(v)
            except json.JSONDecodeError:
                raise ValueError("Content must be a string or JSON-serializable.")
        return v

    @root_validator
    def check_insert_model(cls, values):
        if values["insert_at_row"] is None and values["write_mode"] == "insert":
            raise ValueError("Must provide `insert_at_row` when using `insert` mode.")
        return values


class WriteFile(FileSystemTool):
    description: str = """
        Write content to a file.
        
        {%if root_dir %} Paths must be relative to {{ root_dir }}.{% endif %}}
        
        {%if require_confirmation %} You MUST ask the user to confirm writes by
        showing them details. {% endif %}
        """
    require_confirmation: bool = True

    def run(self, write_content: WriteContent) -> str:
        [path] = self.validate_paths([write_content.path])

        # ensure the parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        if write_content.write_mode == "overwrite":
            with open(path, "w") as f:
                f.write(write_content.content)
        elif write_content.write_mode == "append":
            with open(path, "a") as f:
                f.write(write_content.content)
        elif write_content.write_mode == "insert":
            with open(path, "r") as f:
                contents = f.readlines()
            contents[write_content.insert_at_row] = write_content.content

            with open(path, "w") as f:
                f.writelines(contents)

        return f"Files {write_content.path} written successfully."


class WriteFiles(WriteFile):
    description: str = """
        Write content to multiple files. Each `WriteContent` object in the
        `contents` argument is an instruction to write to a specific file.
        
        {%if root_dir %} Paths must be relative to {{ root_dir }}.{% endif %}}
        
        {%if require_confirmation %} You MUST ask the user to confirm writes by
        showing them details. {% endif %}
        """
    require_confirmation: bool = True

    @validate_arguments
    def run(self, contents: list[WriteContent]) -> str:
        for wc in contents:
            super().run(write_content=wc)
        return f"Files {[c.path for c in contents]} written successfully."
