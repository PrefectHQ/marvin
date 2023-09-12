import subprocess
from pathlib import Path
from typing import Optional

from . import Tool


class Shell(Tool):
    """
    Shell class that inherits from the Tool class.
    This class is used to run arbitrary shell code.
    """

    require_confirmation: bool = True
    working_directory: Optional[Path] = None

    def run(self, cmd: str, working_directory: Optional[str] = None) -> str:  # type: ignore # noqa: E501
        """
        Method to run the shell command.

        Args:
            cmd (str): The shell command to run.
            working_directory (str, optional): The directory in which to run the command
            Defaults to None.

        Raises:
            ValueError: If both instance and method working directories are provided.

        Returns:
            str: The output from the executed shell command.
        """
        if working_directory and self.working_directory:
            raise ValueError(
                f"The working directory is {self.working_directory}; do not provide another one."  # noqa: E501
            )

        wd = working_directory or (
            str(self.working_directory) if self.working_directory else None
        )

        try:
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=wd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            if result.returncode != 0:
                return (
                    f"Command failed with code {result.returncode} and error:"
                    f" {result.stderr.decode() or '<No error>'}"
                )
            else:
                return (
                    "Command succeeded with output:"
                    f" { result.stdout.decode() or '<No output>' }"
                )

        except Exception as e:
            return f"Execution failed: {str(e)}"
