# 🚨 WARNING 🚨
# These functions allow ARBITRARY code execution and should be used with caution.

import subprocess


def shell(command: str) -> str:
    """executes a shell command on your local machine and returns the output"""
    return subprocess.check_output(command, shell=True).decode("utf-8")


def python(code: str) -> str:
    """
    Executes Python code on your local machine and returns the output. You can
    use this to run code that isn't compatible with the code interpreter tool,
    for example if it requires internet access or other packages.
    """
    return str(eval(code))
