# Loaders and Documents
## Motivation
One of the primary limitations of LLMs is the fact that they've only been trained on information found on the internet up to a certain date.

If you want to build an LLM-based app that has the ability to:
- answer questions about current events
- process custom sources of text, like internal Notion docs
- maintain knowledge about the state of itself

... then you'll need a way to update the LLM's knowledge base - and that's where the idea of a `Loader` comes in.

### TL;DR
A `Loader` parses a source of information into a `list[Document]`, which can then be stored as context for the LLM.

<p align="center">
  <img src="../imgs/loader_diagram.png" alt="Image description" width="700">
</p>



## What is a `Document`?
A `Document` is a rich Pydantic model that represents a store-able and searchable unit of information. 

A valid `Document` only requires one attribute, `text`: the raw text of the document. For example:

```python
from marvin.models.document import Document

document = Document(text="This is a document.")
```

You can attach arbitrary `Metadata` to a `Document`. For example:

```python
from marvin.models.document import Document
from marvin.models.metadata import Metadata

my_document = Document(
    text="This is a document.",
    metadata=Metadata(
        title="My Document",
        link="https://www.example.com",
        random_metadata_field="This is very important to me!"
    )
)
```

### Creating excerpts from a `Document`
`Document` offers a `to_excerpts` method that splits a `Document` into a `list[Document]` which are rich excerpts of the original `Document`. For example:

```python
# using the same document as above
my_document.to_excerpts()
```






## What is a `Loader`?

For example, one could create a `FileLoader` that loads documents from a local directory:

```python
from marvin.loaders.base import Loader
from marvin.models.document import Document

class FileLoader(Loader):

    async def load(self) -> list[Document]:
        documents = []
        for file in os.listdir(self.path):
            with open(file) as f:
                documents.append(Document(text=f.read()))
        return documents
```



```python
prefect_source_code = GitHubRepoLoader(
    repo="prefecthq/prefect",
    glob="**/*.py",
    exclude_glob="**/tests/**"
)
```