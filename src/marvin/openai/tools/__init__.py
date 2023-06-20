from marvin.openai.tools.base import Tool
from . import format_response, filesystem, python, shell

TOOL_MAP = {
    "format_response": format_response.FormatResponse,
    "python": python.Python,
    "shell": shell.Shell,
    "read_files": filesystem.ReadFiles,
    "write_files": filesystem.WriteFiles,
    "list_files": filesystem.ListFiles,
}
