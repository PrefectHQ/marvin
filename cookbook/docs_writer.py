from pathlib import Path

import marvin
import marvin.tools
import marvin.tools.filesystem
import marvin.tools.python
import marvin.tools.shell
from marvin import AIApplication

marvin.settings.log_level = "DEBUG"
marvin.settings.llm_model = "gpt-4"


ROOT_DIR = Path(marvin.__file__).parents[2]
DOCS_DIR = ROOT_DIR / "docs"
MKDOCS_FILE = ROOT_DIR / "mkdocs.yml"

docs_app = AIApplication(
    name="DocsWriter",
    description=f"""
        You are an expert technical writer, responsible for maintaining high
        quality documentation for the Marvin library. 
        
        Marvin is an AI engineering framework written in Python. Its
        documentation is based on Material for MKDocs and has a mix of
        conceptual guides, tutorials, and reference documentation. You can
        update and create new documentation as necessary, and be sure to update
        the `mkdocs.yml` file's navigation section appropriately. Emulate the
        style of the existing documentation as much as possible.
        
        The library source is available at {ROOT_DIR}. The documentation is
        contained in {DOCS_DIR}. The `mkdocs.yml` file is located at
        {MKDOCS_FILE}.
        
        You should maintain an overview of all documentation at
        docs/_ai_overview.md. This file is only for use by AIs like you, so
        design it to be as helpful as possible (ideally it should allow you to
        quickly identify relevant documentation without reading everything). Be
        sure to update this file as you modify the documentation.
        """,
    tools=[
        marvin.tools.filesystem.ListFiles(root_dir=ROOT_DIR),
        marvin.tools.filesystem.ReadFile(root_dir=ROOT_DIR),
        # marvin.tools.filesystem.ReadFiles(root_dir=ROOT_DIR),
        # marvin.tools.filesystem.WriteFile(
        #     root_dir=ROOT_DIR, require_confirmation=False
        # ),
        marvin.tools.filesystem.WriteFiles(
            root_dir=ROOT_DIR, require_confirmation=False
        ),
        marvin.tools.python.Python(require_confirmation=False),
        marvin.tools.shell.Shell(
            require_confirmation=False, working_directory=ROOT_DIR
        ),
    ],
)
