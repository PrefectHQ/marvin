from pathlib import Path

import marvin


def write_to_file(content: str, filename: str):
    Path(filename).write_text(content)


def read_file(filename: str) -> str:
    return Path(filename).read_text()


def delete_file(filename: str):
    Path(filename).unlink()


def confirm_with_user(content: str) -> bool:
    """require 'y' or 'yes' to confirm"""
    return input(content).lower() in ("y", "yes")


agent = marvin.Agent(
    tools=[write_to_file, read_file, delete_file, confirm_with_user],
    prompt="use your tools to help the user with their request",
)
agent.run(
    (
        "write a file called 'test.txt' with content 'hello world',"
        "read the file"
        "and then delete the file if the user confirms this"
    ),
)
