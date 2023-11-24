import os
import pathlib
import shutil


def _safe_create_file(path: str) -> None:
    path = os.path.expanduser(path)
    file_path = pathlib.Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.touch(exist_ok=True)


def getcwd() -> str:
    """Returns the current working directory"""
    return os.getcwd()


def write(path: str, contents: str) -> str:
    """Creates or overwrites a file with the given contents"""
    path = os.path.expanduser(path)
    _safe_create_file(path)
    with open(path, "w") as f:
        f.write(contents)
    return f'Successfully wrote "{path}"'


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
    path = os.path.expanduser(path)
    _safe_create_file(path)
    with open(path, "r") as f:
        lines = f.readlines()
        if insert_line < 0:
            insert_line = len(lines) + insert_line + 1
        if mode == "insert":
            lines[insert_line:insert_line] = contents.splitlines(True)
        elif mode == "overwrite":
            lines[insert_line : insert_line + len(contents.splitlines())] = (
                contents.splitlines(True)
            )
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
    path = os.path.expanduser(path)
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
    path = os.path.expanduser(path)
    path = pathlib.Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return f'Successfully created directory "{path}"'


def mv(src: str, dest: str) -> str:
    """Moves a file or directory"""
    src = os.path.expanduser(src)
    dest = os.path.expanduser(dest)
    src = pathlib.Path(src)
    dest = pathlib.Path(dest)
    src.rename(dest)
    return f'Successfully moved "{src}" to "{dest}"'


def cp(src: str, dest: str) -> str:
    """Copies a file or directory"""
    src = os.path.expanduser(src)
    dest = os.path.expanduser(dest)
    src = pathlib.Path(src)
    dest = pathlib.Path(dest)
    shutil.copytree(src, dest)
    return f'Successfully copied "{src}" to "{dest}"'


def ls(path: str) -> str:
    """Lists the contents of a directory"""
    path = os.path.expanduser(path)
    path = pathlib.Path(path)
    return "\n".join(str(p) for p in path.iterdir())
