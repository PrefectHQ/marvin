from pathlib import Path

from pydantic import Field

from marvin.openai.tools import Tool


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
            return [str(p) for p in path.rglob("*") if p.is_file()]
        return [str(p) for p in path.glob("*") if p.is_file()]


class ReadFiles(FileSystemTool):
    description: str = """
    Read the content of files.{% if root_dir %} Paths must be relative to {{
    root_dir }}. Provide '.' instead of '/' to read root.{%- endif %}}
    """

    def run(self, paths: list[str]) -> list[str]:
        """Load content of teach file into a list, prefixed with the file name."""
        content = []
        for path in self.validate_paths(paths):
            with open(path) as f:
                content.append(f"# {path}\n\n{f.read()}")
        return content


class WriteFiles(FileSystemTool):
    description: str = """
        Write content to files. The argument `paths_and_content` is a dictionary
        that maps file paths to content: {"path/to/file": "file content"}
        
        {%if root_dir %} Paths must be relative to {{ root_dir }}.{% endif %}}
        
        {%if require_confirmation %} You MUST ask the user to confirm writes by
        showing them the path and contents. {% endif %}
        """
    require_confirmation: bool = True

    def run(self, paths_and_content: dict[str, str]) -> str:
        paths = self.validate_paths(paths_and_content.keys())
        content = paths_and_content.values()

        for path, content in zip(paths, content):
            # ensure the parent directory exists
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w") as f:
                f.write(content)
        return f"Files {paths} written successfully."
