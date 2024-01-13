# 🚨 WARNING 🚨
# These functions allow ARBITRARY code execution and should be used with caution.

import json
import subprocess


def shell(command: str) -> str:
    """executes a shell command on your local machine and returns the output"""

    result = subprocess.run(command, shell=True, text=True, capture_output=True)

    # Output and error
    output = result.stdout
    error = result.stderr

    return json.dumps(dict(command_output=output, command_error=error))


def python(code: str) -> str:
    """
    Executes Python code on your local machine and returns the output. You can
    use this to run code that isn't compatible with the code interpreter tool,
    for example if it requires internet access or other packages.
    """
    return str(eval(code))
