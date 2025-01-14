import chromadb
import pytest

import marvin
from marvin.memory.providers.chroma import ChromaMemory


class TestMemory:
    def test_store_and_retrieve(self):
        m = marvin.Memory(key="test", instructions="test")
        m.add("The number is 42")
        result = m.search("numbers")
        assert len(result) == 1
        assert "The number is 42" in result.values()

    def test_delete(self):
        m = marvin.Memory(key="test", instructions="test")
        m_id = m.add("The number is 42")
        m.delete(m_id)
        result = m.search("numbers")
        assert len(result) == 0

    def test_search(self):
        m = marvin.Memory(key="test", instructions="test")
        m.add("The number is 42")
        m.add("The number is 43")
        result = m.search("numbers")
        assert len(result) == 2
        assert "The number is 42" in result.values()
        assert "The number is 43" in result.values()


class TestMemoryProvider:
    def test_load_from_string_invalid(self):
        with pytest.raises(ValueError):
            marvin.Memory(key="test", instructions="test", provider="invalid")

    def test_load_from_string_chroma_db(self):
        m = marvin.Memory(key="test", instructions="test", provider="chroma-db")
        assert isinstance(m.provider, ChromaMemory)

    def test_load_from_instance(self, tmp_path):
        mp = ChromaMemory(
            client=chromadb.PersistentClient(path=str(tmp_path / "test_path")),
        )
        m = marvin.Memory(key="test", instructions="test", provider=mp)
        assert m
