# Infra

!!! warning "Construction zone"
    This area of the docs is under active development and may change.
## Chroma 
Marvin [provides a simple wrapper](https://github.com/PrefectHQ/marvin/blob/main/src/marvin/infra/chroma.py) of the ChromaDB client to make it easier to interact with the database.

Read the [ChromaDB usage guide](https://docs.trychroma.com/usage-guide) for more information.

!!! warning "ChromaDB has a large memory footprint"
    ChromaDB uses `sentence-transformers` by default for embeddings, which requires `torch`. [`torch` has recently
    added wheels for Python 3.11](https://pypi.org/project/torch/2.0.0/#files).

    Although Marvin uses OpenAI's "text-embedding-ada-002" model offered via `chromadb.utils.embedding_functions`,
    `chromadb` enforces the `sentence-transformers` dependency at this time.

### Relevance to Marvin
ChromaDB is an embeddings database that is used by Marvin to store and query document embeddings.

When you call `.load_and_store()` on a `Loader`, you are calling `Chroma.add` to store documents in the default collection.

`load_and_store` accepts an optional `topic_name` that corresponds to a collection in ChromaDB. If you want to store documents in a different collection, simply pass a different `topic_name` to `load_and_store` and the collection will be created for you or updated.

### Usage
If desired, you can use it directly:

#### Querying
```python
from marvin.infra.chroma import Chroma

async with Chroma() as chroma:
    query_results: dict[str, list] = await chroma.query(
        query_texts=["some natural language query"],
        where={"some_metadata_field": "has_this_value"},
        include=["documents", "metadatas"], # "ids" are always included
    )
```

#### Adding
```python
from marvin.infra.chroma import Chroma

async with Chroma(collection_name="my-new-collection") as chroma:
    await chroma.add(
        documents=["some text", "some other text"],
        metadatas=[{"some_metadata_field": "some_value"}, {"some_metadata_field": "some_other_value"}],
    )
```