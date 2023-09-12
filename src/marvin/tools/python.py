import sys
from io import StringIO
from typing import Any, Optional

from . import Tool


def run_python(
    code: str,
    globals: Optional[dict[str, Any]] = None,
    locals: Optional[dict[str, Any]] = None,
) -> str:
    """
    Executes the provided Python code and captures the output.

    Args:
        code (str): The Python code to execute.
        globals (Optional[Dict[str, Any]]): The global variables to use during execution
        locals (Optional[Dict[str, Any]]): The local variables to use during execution.

    Returns:
        str: The output from the executed Python code.
    """
    old_stdout = sys.stdout
    new_stdout = StringIO()
    sys.stdout = new_stdout
    try:
        exec(code, globals or {}, locals or {})
        output = new_stdout.getvalue()
    except Exception as e:
        output = repr(e)
    finally:
        sys.stdout = old_stdout
    return output


class Python(Tool):
    """
    A tool for running arbitrary Python code.

    Attributes:
        description (str): A description of the tool.
        require_confirmation (bool): Whether the user must confirm execution.
    """

    description: str = """
    Runs arbitrary Python code.

    {%if require_confirmation %} You MUST ask the user to confirm execution by
    showing them the code. {% endif %}
    """
    require_confirmation: bool = True

    def run(self, code: str, *args: Any, **kwargs: Any) -> str:  # type: ignore
        """
        Executes the provided Python code using the run_python function.

        Args:
            code (str): The Python code to execute.

        Returns:
            str: The output from the executed Python code.
        """
        return run_python(code)
