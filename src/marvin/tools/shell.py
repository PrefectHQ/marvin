import subprocess
from pathlib import Path

from marvin.tools import Tool


class Shell(Tool):
    description: str = """
    Runs arbitrary shell code.
    
    {% if working_directory %} The working directory will be {{
    working_directory }}. {% endif %}.

    {%if require_confirmation %} You MUST ask the user to confirm execution by
    showing them the code. {% endif %}
    """
    require_confirmation: bool = True
    working_directory: Path = None

    def run(self, cmd: str, working_directory: str = None) -> str:
        if working_directory and self.working_directory:
            raise ValueError(
                f"The working directoy is {self.working_directory}; do not provide"
                " another one."
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
