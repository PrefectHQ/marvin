import sys
from io import StringIO

from marvin.tools import Tool


def run_python(code: str, globals: dict = None, locals: dict = None):
    old_stdout = sys.stdout
    new_stdout = StringIO()
    sys.stdout = new_stdout
    try:
        exec(code, globals or {}, locals or {})
        result = new_stdout.getvalue()
    except Exception as e:
        result = repr(e)
    finally:
        sys.stdout = old_stdout
    return result


class Python(Tool):
    description: str = """
    Runs arbitrary Python code.

    {%if require_confirmation %} You MUST ask the user to confirm execution by
    showing them the code. {% endif %}
    """
    require_confirmation: bool = True

    def run(self, code: str) -> str:
        return run_python(code)
