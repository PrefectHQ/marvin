import uuid
from dataclasses import dataclass, field
from typing import Callable

import sqlalchemy
from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, String, select, text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy_utils import create_database, database_exists

from marvin.memory.memory import MemoryProvider

try:
    # For embeddings, we can use langchain_openai or any other library:
    from langchain_openai import OpenAIEmbeddings
except ImportError:
    raise ImportError(
        "To use an embedding function similar to LanceDB's default, "
        "please install lancedb with: pip install lancedb"
    )

# SQLAlchemy base class for declarative models
Base = declarative_base()


class SQLMemoryTable(Base):
    """
    A simple declarative model that represents a memory record.

    We'll dynamically set the __tablename__ at runtime.
    """

    __abstract__ = True
    id = Column(String, primary_key=True)
    text = Column(String)
    # Use pgvector for storing embeddings in a Postgres Vector column
    # vector = Column(Vector(dim=1536))  # Adjust dimension to match your embedding model


@dataclass(kw_only=True)
class PostgresMemory(MemoryProvider):
    """
    A ControlFlow MemoryProvider that stores text + embeddings in PostgreSQL
    using SQLAlchemy and pg_vector. Each Memory module gets its own table.
    """

    database_url: str = field(
        default="postgresql://user:password@localhost:5432/your_database",
        metadata={
            "description": "SQLAlchemy-compatible database URL to a Postgres instance with pgvector."
        },
    )
    table_name: str = field(
        default="memory_{key}",
        metadata={
            "description": """
            Name of the table to store this memory partition. "{key}" will be replaced 
            by the memory's key attribute.
            """
        },
    )
    embedding_dimension: int = field(
        default=1536,
        metadata={
            "description": "Dimension of the embedding vectors. Match your model's output."
        },
    )
    embedding_fn: Callable = field(
        default_factory=lambda: OpenAIEmbeddings(
            model="text-embedding-ada-002",
        ),
        metadata={"description": "A function that turns a string into a vector."},
    )

    # Internal: keep a cached Session maker
    _SessionLocal: sessionmaker | None = None
    # This dict will map "table_name" -> "model class"
    _table_class_cache: dict[str, Base] = {}

    def configure(self, memory_key: str) -> None:
        """
        Configure a SQLAlchemy session and ensure the table for this
        memory partition is created if it does not already exist.
        """
        engine = sqlalchemy.create_engine(self.database_url)

        # 2) If DB doesn't exist, create it!
        if not database_exists(engine.url):
            create_database(engine.url)

        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()

        self._SessionLocal = sessionmaker(bind=engine)

        # Dynamically create a specialized table model for this memory_key
        table_name = self.table_name.format(key=memory_key)

        # 1) Check if table already in metadata
        if table_name not in Base.metadata.tables:
            # 2) Create the dynamic class + table
            memory_model = type(
                f"SQLMemoryTable_{memory_key}",
                (SQLMemoryTable,),
                {
                    "__tablename__": table_name,
                    "vector": Column(Vector(dim=self.embedding_dimension)),
                },
            )

            try:
                Base.metadata.create_all(engine, tables=[memory_model.__table__])
                # Store it in the cache
                self._table_class_cache[table_name] = memory_model
            except ProgrammingError as e:
                raise RuntimeError(f"Failed to create table {table_name}: {e}")

    def _get_session(self) -> Session:
        if not self._SessionLocal:
            raise RuntimeError(
                "Session is not initialized. Make sure to call configure() first."
            )
        return self._SessionLocal()

    def _get_table(self, memory_key: str) -> Base:
        """
        Return a dynamically generated declarative model class
        mapped to the memory_{key} table. Each memory partition
        has a separate table.
        """
        table_name = self.table_name.format(key=memory_key)

        # Return the cached class if already built
        if table_name in self._table_class_cache:
            return self._table_class_cache[table_name]

        # If for some reason it's not there, create it now (or raise error):
        memory_model = type(
            f"SQLMemoryTable_{memory_key}",
            (SQLMemoryTable,),
            {
                "__tablename__": table_name,
                "vector": Column(Vector(dim=self.embedding_dimension)),
            },
        )
        self._table_class_cache[table_name] = memory_model
        return memory_model

    def add(self, memory_key: str, content: str) -> str:
        """
        Insert a new memory record into the Postgres table,
        generating an embedding and storing it in a vector column.
        Returns the memory's ID (uuid).
        """
        memory_id = str(uuid.uuid4())
        model_cls = self._get_table(memory_key)

        # Generate an embedding for the content
        embedding = self.embedding_fn.embed_query(content)

        with self._get_session() as session:
            record = model_cls(id=memory_id, text=content, vector=embedding)
            session.add(record)
            session.commit()

        return memory_id

    def delete(self, memory_key: str, memory_id: str) -> None:
        """
        Delete a memory record by its UUID.
        """
        model_cls = self._get_table(memory_key)

        with self._get_session() as session:
            session.query(model_cls).filter(model_cls.id == memory_id).delete()
            session.commit()

    def search(self, memory_key: str, query: str, n: int = 20) -> dict[str, str]:
        """
        Uses pgvector's approximate nearest neighbor search with the `<->` operator to find
        the top N matching records for the embedded query. Returns a dict of {id: text}.
        """
        model_cls = self._get_table(memory_key)
        # Generate embedding for the query
        query_embedding = self.embedding_fn.embed_query(query)
        embedding_col = model_cls.vector

        with self._get_session() as session:
            results = session.execute(
                select(model_cls.id, model_cls.text)
                .order_by(embedding_col.l2_distance(query_embedding))
                .limit(n)
            ).all()

        return {row.id: row.text for row in results}
