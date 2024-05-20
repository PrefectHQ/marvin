import glob as glob_module
import os
import shutil
from pathlib import Path


def _safe_create_file(path: str) -> Path:
    file_path = Path(path).expanduser()
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.touch(exist_ok=True)
    return file_path


def getcwd() -> str:
    """Returns the current working directory"""
    return os.getcwd()


def write(path: str, contents: str) -> str:
    """Creates or overwrites a file with the given contents"""
    path = _safe_create_file(path)
    path.write_text(contents)
    return f'Successfully wrote "{path}"'


def generate_constrained_write(root: str) -> str:
    """
    Returns a `write` function that will only write to files under the given root directory.
    """

    def constrained_write(path: str, contents: str) -> str:
        """
        Write `contents` to a `path`.
        """
        path: Path = Path(path).expanduser().absolute()
        root_path = Path(root).expanduser().absolute()

        if root_path not in path.parents:
            raise ValueError(
                f'Cannot write to "{path}". It\'s not under the root directory "{root_path}"'
            )

        return write(path, contents)

    constrained_write.__doc__ = (
        write.__doc__
        + f'\n\nNote: this function is constrained to files under "{root}".'
    )
    return constrained_write


def delete(path: str, is_dir: bool = False) -> str:
    """Deletes a file or directory based on the is_dir flag."""
    path = Path(path).expanduser()

    if is_dir:
        if path.is_dir():
            shutil.rmtree(path)  # Recursively delete directory and its contents
            return f'Successfully deleted directory "{path}"'
        else:
            return f'Error: "{path}" is not a directory.'
    else:
        if path.is_file():
            path.unlink()  # Delete the file
            return f'Successfully deleted "{path}"'
        else:
            return f'Error: "{path}" is not a file or does not exist.'


def generate_constrained_delete(root: str) -> str:
    """
    Returns a `delete` function that will only write to files under the given root directory.
    """

    def constrained_delete(path: str, is_dir: bool = False) -> str:
        """
        Delete a file or directory at `path`.
        """
        path: Path = Path(path).expanduser().absolute()
        root_path = Path(root).expanduser().absolute()

        if root_path not in path.parents:
            raise ValueError(
                f'Cannot delete "{path}". It\'s not under the root directory "{root_path}"'
            )

        return delete(path, is_dir=is_dir)

    constrained_delete.__doc__ = (
        delete.__doc__
        + f'\n\nNote: this function is constrained to files under "{root}".'
    )

    return constrained_delete


def write_lines(
    path: str, contents: str, insert_line: int = -1, mode: str = "insert"
) -> str:
    """Writes content to a specific line in the file.

    Args:
        path (str): The name of the file to write to.
        contents (str): The content to write to the file.
        insert_line (int, optional): The line number to insert the content at.
            Negative values count from the end of the file. Defaults to -1.
        mode (str, optional): The mode to use when writing the content. Can be
            "insert" or "overwrite". Defaults to "insert".

    Returns:
        str: A message indicating whether the write was successful.
    """
    path = _safe_create_file(path)
    with open(path, "r") as f:
        lines = f.readlines()
        if insert_line < 0:
            insert_line = len(lines) + insert_line + 1
        if mode == "insert":
            lines[insert_line:insert_line] = contents.splitlines(True)
        elif mode == "overwrite":
            lines[
                insert_line : insert_line + len(contents.splitlines())
            ] = contents.splitlines(True)
        else:
            raise ValueError(f"Invalid mode: {mode}")
    with open(path, "w") as f:
        f.writelines(lines)
    return f'Successfully wrote to "{path}"'


def read(path: str, include_line_numbers: bool = False) -> str:
    """Reads a file and returns the contents.

    Args:
        path (str): The path to the file.
        include_line_numbers (bool, optional): Whether to include line numbers
            in the returned contents. Defaults to False.

    Returns:
        str: The contents of the file.
    """
    path = Path(path).expanduser()
    with open(path, "r") as f:
        if include_line_numbers:
            lines = f.readlines()
            lines_with_numbers = [f"{i+1}: {line}" for i, line in enumerate(lines)]
            return "".join(lines_with_numbers)
        else:
            return f.read()


def read_lines(
    path: str,
    start_line: int = 0,
    end_line: int = -1,
    include_line_numbers: bool = False,
) -> str:
    """Reads a partial file and returns the contents with optional line numbers.

    Args:
        path (str): The path to the file.
        start_line (int, optional): The starting line number to read. Defaults
            to 0.
        end_line (int, optional): The ending line number to read. Defaults to
            -1, which means read until the end of the file.
        include_line_numbers (bool, optional): Whether to include line numbers
            in the returned contents. Defaults to False.

    Returns:
        str: The contents of the file.
    """
    path = os.path.expanduser(path)
    with open(path, "r") as f:
        lines = f.readlines()
        if start_line < 0:
            start_line = len(lines) + start_line
        if end_line < 0:
            end_line = len(lines) + end_line
        if include_line_numbers:
            lines_with_numbers = [
                f"{i+1}: {line}" for i, line in enumerate(lines[start_line:end_line])
            ]
            return "".join(lines_with_numbers)
        else:
            return "".join(lines[start_line:end_line])


def mkdir(path: str) -> str:
    """Creates a directory (and any parent directories))"""
    path = Path(path).expanduser()
    path.mkdir(parents=True, exist_ok=True)
    return f'Successfully created directory "{path}"'


def mv(src: str, dest: str) -> str:
    """Moves a file or directory"""
    src = Path(src).expanduser()
    dest = Path(dest).expanduser()
    src.rename(dest)
    return f'Successfully moved "{src}" to "{dest}"'


def cp(src: str, dest: str) -> str:
    """Copies a file or directory"""
    src = Path(src).expanduser()
    dest = Path(dest).expanduser()
    shutil.copytree(src, dest)
    return f'Successfully copied "{src}" to "{dest}"'


def ls(path: str) -> str:
    """Lists the contents of a directory"""
    path = Path(path).expanduser()
    return "\n".join(str(p) for p in path.iterdir())


def glob(pattern: str) -> list[str]:
    """
    Returns a list of paths matching a valid glob pattern. The pattern can
    include ** for recursive matching, such as '/path/**/dir/*.py'. Only simple
    glob patterns are supported, compound queries like '/path/*.{py, md}' are
    NOT supported.
    """
    return glob_module.glob(pattern, recursive=True)


def concat(source_paths: list[str], dest_path: str, add_headers: bool = True) -> str:
    """
    Concatenates the contents of multiple source files into a single destination
    file. The result should be markdown. If add_headers is True, the file path
    will be added as a header above the contents of each file.

    Note that source paths can include simple glob patterns, such as
    '/path/**/dir/*.py'. Compound queries like '/path/*.{py, md}' are NOT
    supported.
    """
    # source_paths can include glob patterns
    source_paths = [path for pattern in source_paths for path in glob(pattern)]

    dest_path = _safe_create_file(dest_path)
    with open(dest_path, "w") as dest_file:
        for source_path in source_paths:
            source_path = os.path.expanduser(source_path)
            if add_headers:
                dest_file.write(f"\n\n# File: {source_path}\n")
            with open(source_path, "r") as source_file:
                dest_file.write(source_file.read())
    return f'Successfully concatenated files to "{dest_path}"'


def generate_constrained_concat(root: str) -> callable:
    """
    Returns a `concat` function that will only concatenate files under the given root directory.
    """

    def constrained_concat(
        source_paths: list[str], dest_path: str, add_headers: bool = True
    ) -> str:
        root_path = Path(root).expanduser().absolute()

        # Check if destination path is under root directory
        dest_path_abs = Path(dest_path).expanduser().absolute()
        if root_path not in dest_path_abs.parents and dest_path_abs != root_path:
            raise ValueError(
                f'Cannot write to "{dest_path_abs}". It\'s not under the root directory "{root_path}"'
            )

        # Proceed with concatenation
        return concat(source_paths, dest_path, add_headers=add_headers)

    constrained_concat.__doc__ = (
        concat.__doc__
        + f'\n\nNote: this function is constrained to files under "{root}".'
    )

    return constrained_concat
