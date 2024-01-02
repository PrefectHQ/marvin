from pathlib import Path

import marvin
import marvin.tools
import marvin.tools.filesystem
import marvin.tools.python
import marvin.tools.shell
from marvin.beta.applications import AIApplication

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
        the `mkdocs.yml` file's navigation section appropriately. 
        
        When crafting Marvin's documentation, your aim should be for a tone that
        is professional yet conversational. Our writing style prioritizes
        clarity and understandability, utilizing plain English and circumventing
        unnecessary jargon. We believe in demystifying complex concepts through
        the use of metaphors and analogies, likening Marvin to a "Swiss Army
        Knife" to denote its multitude of functions. Your content should be
        structured into digestible chunks, with each segment focusing on a
        singular idea or topic. Effective organization of your sections through
        headers, listing details with bullet points, and conveying technical
        specifications with code blocks are highly encouraged. Hyperlinks are
        integral in guiding readers to pertinent content both within and outside
        the document. Aim to establish a sense of community by directly
        addressing our readers with words like "we" and "you." Marvin's
        documentation is not merely a technical manual; it mirrors our
        inclusive, innovative, and audacious personality. While we do value
        humor and wit, referencing Marvin's cultural background in the
        Hitchhiker's Guide to the Galaxy, it should be used sparingly and
        fittingly to maintain its charm and effectiveness. Remember, our goal
        with our writing is not just to inform, but to engage, inspire, and
        occasionally elicit a smile from our readers.
        
        The library source is available at {ROOT_DIR}. The documentation is
        contained in {DOCS_DIR}. The `mkdocs.yml` file is located at
        {MKDOCS_FILE}.
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
