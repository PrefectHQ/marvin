import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.config import Settings
from marvin.plugins.base import Plugin
from pydantic import Field

class SearchChromaEmbeddings(Plugin):
    description: str = Field(
        "Retrieve relevant embeddings from a chroma database. Useful when asked"
        " about specific pieces of knowledge that you're unfamiliar with."
    )
    chroma_settings: Settings = Field(
        default_factory=Settings,
        description="Settings for the chroma database",
    )
    
    async def get_collection(self, name: str = "default") -> Collection:
        client = chromadb.Client(self.chroma_settings)
        return client.get_collection(name=name)
    
    async def run(
        self,
        collection_name: str,
        query_texts: list[str],
        n_results: int = 2,
        **kwargs
    ):
        collection = await self.get_collection(name=collection_name)
        results = collection.query(
            query_texts=query_texts,
            n_results=n_results,
            **kwargs
        )
        print(results)
        return "\n\n".join(
            f"{r['text']} ({r['score']}): {r['embedding']}"
            for r in results
        )
    
if __name__ == "__main__":
    import asyncio
    from marvin.bots import Bot
    
    bot = Bot(
        personality="Marvin the Paranoid Android from The Hitchhiker's Guide to the Galaxy",
        plugins=[SearchChromaEmbeddings()],
    )
    
    asyncio.run(bot.say("what's new in prefect 2?"))