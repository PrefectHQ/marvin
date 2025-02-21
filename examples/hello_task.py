"""Warning: this example will run untrusted shell commands.

Use with caution.
"""

import platform
import subprocess

from pydantic import IPvAnyAddress

import marvin


def run_shell_command(command: list[str]) -> str:
    """e.g. ['ls', '-l'] or ['git', 'diff', '|', 'grep', 'some_code']"""
    return subprocess.check_output(command).decode()


task = marvin.Task(
    instructions="find the current ip address",
    result_type=IPvAnyAddress,
    tools=[run_shell_command],
    context={"os": platform.system()},
)

task.run()
