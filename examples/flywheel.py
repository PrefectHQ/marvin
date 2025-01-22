"""
A knowledge flywheel leveraging Marvin's memory (vector store)
to store and refine typed nodes in a schema-less knowledge graph.

Highlights:
1) Minimal typed data structures: Node, Relationship.
2) One agent, using a single Memory to store + retrieve knowledge snippets (JSON).
3) On each observation, the agent merges new info into the graph (synonyms, relationships).
4) 'ls' and 'rm' are direct user commands (not routed through the LLM).
5) No advanced indexing or relational DB—everything goes into Marvin's vector-based Memory.
   We rely on the LLM to unify and refine knowledge as we re-load/merge data.

Goal:
 - Demonstrate how we can, from text alone, maintain an ever-evolving graph of typed data.
 - Each input can update or refine the "schema space" by linking new or existing nodes.
 - No classical OOP or inheritance; just typed nodes and edges connected in a web.

Usage:
  python flywheel.py

Commands:
  - ls    : Show all known nodes and relationships
  - rm    : Remove all stored knowledge
  - exit  : Quit
  - other : Parse text as a new observation, unify or create graph updates

Keep in mind this MVP is a stepping-stone.
Real expansions might unify duplicates more intelligently, handle versioning, etc.
"""

import json
from typing import Any

from pydantic import BaseModel, Field

import marvin
from marvin.memory import Memory
from marvin.memory.providers.chroma import ChromaPersistentMemory


class Relationship(BaseModel):
    """Edge in a knowledge graph."""

    subject: str
    relation: str
    object: str


class Node(BaseModel):
    """
    A typed concept.
    type: classification of entity (e.g. 'person', 'cat', 'location')
    synonyms: alternative references (e.g. "my cat", "Garfield").
    properties: attribute dict that can store arbitrary info.
    relationships: edges from THIS node to others
    """

    name: str
    type: str
    synonyms: list[str] = Field(default_factory=list)
    properties: dict[str, str] = Field(default_factory=dict)
    relationships: list[Relationship] = Field(default_factory=list)


class GraphUpdate(BaseModel):
    """Collection of Node updates for a single observation."""

    updates: list[Node] = Field(default_factory=list)


class KnowledgeFlywheel:
    """
    We store a single Memory partition ("knowledge_flywheel") for all nodes.
    Each time we unify or add nodes, we store them as JSON strings in memory.
    On 'ls', we retrieve them with a broad search, unify them in memory, then display.
    On new observation, we pass context + user input to the LLM -> GraphUpdate -> unify & store.
    """

    def __init__(self):
        # A local persistent Chroma-based vector memory at ./knowledge_flywheel
        self.memory = Memory(
            key="knowledge_flywheel",
            provider=ChromaPersistentMemory(
                path=str(marvin.settings.home_path / "knowledge_flywheel")
            ),
            instructions=(
                "Store or retrieve JSON-serialized Node data that represent our knowledge graph."
            ),
        )
        self.agent = marvin.Agent(
            tools=[],
            memories=[self.memory],
            prompt=(
                "You are a knowledge-engine agent. You unify references and refine a typed graph.\n"
                "Output data as GraphUpdate (a list of Node structures) to represent new or updated knowledge."
            ),
        )

    def list_all(self) -> str:
        """Load all Node data from memory, unify them in Python, then print a summary."""
        # fetch everything with a blank search
        entries = self.memory.search("")
        if not entries:
            return "No knowledge stored yet."

        # parse all nodes
        nodes: list[Node] = []
        for content in entries.values():
            try:
                node = Node.model_validate_json(content)
                nodes.append(node)
            except Exception:
                pass

        # We'll do a naive print: nodes, their synonyms, properties, relationships
        # In a real system we'd unify synonyms across these lumps.
        lines: list[str] = []
        for n in nodes:
            syns = f" (synonyms: {n.synonyms})" if n.synonyms else ""
            props = n.properties if n.properties else {}
            lines.append(f"Node: {n.name}{syns} {props}")
            for r in n.relationships:
                lines.append(f"  -> {r.subject} --{r.relation}--> {r.object}")
        return "\n".join(lines)

    def remove_all(self) -> str:
        entries = self.memory.search("")
        for doc_id in entries.keys():
            self.memory.delete(doc_id)
        return "All knowledge cleared."

    def integrate_observation(self, text: str) -> str:
        """
        1) Retrieve existing knowledge from memory to provide context.
        2) Marvin.cast the user input into a GraphUpdate model, prompting the LLM to unify references.
        3) Merge each Node from GraphUpdate into memory:
           - Only merge nodes of the same type with matching names/synonyms
           - Otherwise, store as a new node
        """
        # context: gather known node data, so the LLM can unify references
        existing_docs = self.memory.search("", n=1000)
        known_nodes: list[dict[str, Any]] = []
        for doc in existing_docs.values():
            try:
                known_nodes.append(json.loads(doc))
            except Exception:
                pass

        existing_context = [
            {
                "name": nd.get("name"),
                "type": nd.get("type"),
                "synonyms": nd.get("synonyms", []),
                "properties": nd.get("properties", {}),
            }
            for nd in known_nodes
        ]
        instructions = (
            f"Known nodes:\n{json.dumps(existing_context, indent=2)}\n\n"
            "Create separate nodes for distinct entities (e.g. a person vs a cat).\n"
            "Each node MUST have a 'type' field describing the entity (e.g. 'person', 'cat', 'location').\n"
            "Only unify nodes if they clearly represent the same entity of the same type."
        )

        graph_update = marvin.cast(
            text,
            target=GraphUpdate,
            instructions=instructions,
        )

        # unify each new Node with existing if types match and synonyms overlap
        merges = 0
        creates = 0

        def unify_to_memory(node: Node):
            nonlocal merges, creates
            # check if existing doc matches
            for doc_id, content in existing_docs.items():
                try:
                    existing_node = Node.model_validate_json(content)
                except Exception:
                    continue

                # Only consider merging if types match
                if existing_node.type != node.type:
                    continue

                lower_all = {existing_node.name.lower()} | {
                    s.lower() for s in existing_node.synonyms
                }
                if node.name.lower() in lower_all or any(
                    s.lower() in lower_all for s in node.synonyms
                ):
                    # Merge since types match and names overlap
                    existing_node.synonyms = list(
                        set(existing_node.synonyms + node.synonyms + [node.name])
                    )
                    existing_node.properties.update(node.properties)
                    existing_node.relationships.extend(node.relationships)
                    self.memory.delete(doc_id)
                    self.memory.add(existing_node.model_dump_json())
                    merges += 1
                    return

            # If no match found or types different, create new node
            self.memory.add(node.model_dump_json())
            creates += 1

        for n in graph_update.updates:
            unify_to_memory(n)

        return f"Merged {merges} nodes, created {creates} new nodes."


#
# REPL
#
def main():
    fw = KnowledgeFlywheel()
    print("Knowledge Flywheel. Type 'ls' to list, 'rm' to remove all, 'exit' to quit.")
    while True:
        user_input = input("\nObservation> ").strip()
        if user_input.lower() in ("exit", "quit"):
            print("Goodbye.")
            break
        if user_input.lower() == "ls":
            print(fw.list_all())
            continue
        if user_input.lower() == "rm":
            print(fw.remove_all())
            continue
        print(fw.integrate_observation(user_input))


if __name__ == "__main__":
    main()
