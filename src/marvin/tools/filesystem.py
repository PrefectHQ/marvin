import os
import pathlib
import shutil


def getcwd() -> str:
    """Returns the current working directory"""
    return os.getcwd()


def write(filename: str, contents: str) -> str:
    """Creates or overwrites a file with the given contents"""
    with open(filename, "w") as f:
        f.write(contents)
    return f'Successfully wrote "{filename}"'


def write_lines(
    filename: str, contents: str, insert_line: int = -1, mode: str = "insert"
) -> str:
    """Writes content to a specific line in the file.

    Args:
        filename (str): The name of the file to write to.
        contents (str): The content to write to the file.
        insert_line (int, optional): The line number to insert the content at.
            Negative values count from the end of the file. Defaults to -1.
        mode (str, optional): The mode to use when writing the content. Can be
            "insert" or "overwrite". Defaults to "insert".

    Returns:
        str: A message indicating whether the write was successful.
    """
    with open(filename, "r") as f:
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
    with open(filename, "w") as f:
        f.writelines(lines)
    return f'Successfully wrote to "{filename}"'


def read(filename: str) -> str:
    """Reads a file and returns the contents"""
    with open(filename, "r") as f:
        return f.read()


def read_lines(filename: str, start_line: int = 0, end_line: int = -1) -> str:
    """Reads a partial file and returns the contents"""
    with open(filename, "r") as f:
        lines = f.readlines()
        if start_line < 0:
            start_line = len(lines) + start_line
        if end_line < 0:
            end_line = len(lines) + end_line
        return "".join(lines[start_line:end_line])


def mkdir(path: str) -> str:
    """Creates a directory (and any parent directories))"""
    path = pathlib.Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return f'Successfully created directory "{path}"'


def mv(src: str, dest: str) -> str:
    """Moves a file or directory"""
    src = pathlib.Path(src)
    dest = pathlib.Path(dest)
    src.rename(dest)
    return f'Successfully moved "{src}" to "{dest}"'


def cp(src: str, dest: str) -> str:
    """Copies a file or directory"""
    src = pathlib.Path(src)
    dest = pathlib.Path(dest)
    shutil.copytree(src, dest)
    return f'Successfully copied "{src}" to "{dest}"'


def ls(path: str) -> str:
    """Lists the contents of a directory"""
    path = pathlib.Path(path)
    return "\n".join(str(p) for p in path.iterdir())
