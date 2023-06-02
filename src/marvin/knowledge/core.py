import asyncio
from typing import List, Optional

import matplotlib.pyplot as plt
import networkx as nx
from marvin.infra.chroma import Chroma
from marvin.models.documents import Document
from marvin.models.threads import Message


class KnowledgeGraph:
    def __init__(self, chroma: Chroma = None):
        self.graph = nx.Graph()
        self.chroma = chroma or Chroma

    def add_documents(self, documents: List[Document]):
        """Adds a list of documents to the graph."""
        for doc in documents:
            self.graph.add_node(doc.id, data=doc)

    def draw(self):
        plt.figure(figsize=(8, 6))
        nx.draw(self.graph, with_labels=True)
        plt.show()

    async def update_graph_with_chroma(
        self, query_texts: Optional[List[str]] = None, n_results: int = 10
    ):
        """Updates the graph based on queries to the Chroma collection."""
        async with self.chroma() as chroma:
            results = await chroma.query(
                query_texts=query_texts,
                n_results=n_results,
                include=["distances", "documents"],
            )

            # Check if the query returned any results
            if all(results[i] is not None for i in ["ids", "distances", "documents"]):
                # Iterate over each list of results corresponding to each query
                for query, ids, distances, documents in zip(
                    query_texts,
                    results["ids"],
                    results["distances"],
                    results["documents"],
                ):
                    # Update the graph with new nodes and edges
                    for doc_id, distance, document in zip(ids, distances, documents):
                        # Create new Document object if necessary
                        if doc_id not in self.graph:
                            doc = Document(id=doc_id, text=document)
                            self.graph.add_node(doc.id, data=doc)

                        # Add an edge from the query to the result document in the graph
                        # convert distance to similarity for edge weight
                        self.graph.add_edge(query, doc_id, weight=1 - distance)

    async def update_knowledge_graph_from_messages(
        self,
        messages: List[Message],
    ):
        self.add_documents(
            documents=[
                Document(id=message.id, text=message.content) for message in messages
            ]
        )

        await self.update_graph_with_chroma(
            query_texts=[message.content for message in messages]
        )


if __name__ == "__main__":

    async def main():
        from marvin.bot import Bot

        bot = Bot()
        knowledge_graph = KnowledgeGraph()

        for content in [
            "blocks",
            "flow",
            "python",
            "task",
            "concurrency",
            "async",
            "await",
            "subflow",
        ]:
            await bot.history.add_message(Message(content=content, role="user"))

        messages = await bot.history.get_messages()
        await knowledge_graph.update_knowledge_graph_from_messages(messages)

        print(knowledge_graph.draw())

    asyncio.run(main())
