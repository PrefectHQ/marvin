import asyncio
from collections import defaultdict
from random import randrange
from typing import Dict, Iterable

from pydantic import BaseModel


class Geometry(BaseModel):
    dimension: int
    width: int

    @property
    def cartesian_size(self) -> int:
        return self.width**self.dimension


class Node(BaseModel):
    index: int


class Edge(BaseModel):
    head: Node
    tail: Node

    def __hash__(self):
        return hash((self.head.index, self.tail.index))

    def __eq__(self, other):
        return (
            self.head.index == other.head.index and self.tail.index == other.tail.index
        )


class UnionFind:
    def __init__(self):
        self.parents = {}
        self.ranks = {}

    def find(self, x):
        if x not in self.parents:
            self.parents[x] = x
            self.ranks[x] = 1
            return x
        elif self.parents[x] == x:
            return x
        else:
            self.parents[x] = self.find(self.parents[x])
            return self.parents[x]

    def union(self, x, y):
        root_x = self.find(x)
        root_y = self.find(y)

        if root_x == root_y:
            return

        if self.ranks[root_x] < self.ranks[root_y]:
            root_x, root_y = root_y, root_x

        self.parents[root_y] = root_x
        self.ranks[root_x] += self.ranks[root_y]

    @classmethod
    def from_edges(cls, edges: Iterable[Edge]):
        uf = cls()
        for edge in edges:
            uf.union(edge.head.index, edge.tail.index)
        return uf


async def evolve(p: float, geometry: Geometry = Geometry(dimension=2, width=32)):
    N = geometry.cartesian_size
    total_possible_edges = N * geometry.dimension
    num_edges_to_generate = int(total_possible_edges * p)

    random_numbers = [
        (randrange(N), randrange(geometry.dimension), geometry.width)
        for _ in range(num_edges_to_generate)
    ]

    uf = UnionFind.from_edges(
        Edge(head=Node(index=i), tail=Node(index=i + w**d))
        for i, d, w in random_numbers
    )

    cluster_sizes: Dict[int, int] = defaultdict(int)
    for node in range(N):
        cluster_sizes[uf.find(node)] += 1

    return max(cluster_sizes.values())


async def main():
    import matplotlib.pyplot as plt

    largest_cluster_sizes = await asyncio.gather(
        *[evolve(p / 1000) for p in range(0, int(1e3), 1)]
    )

    plt.plot(largest_cluster_sizes)
    plt.xlabel("Number of iterations")
    plt.ylabel("Size of largest cluster")
    plt.show()


if __name__ == "__main__":
    asyncio.run(main())
