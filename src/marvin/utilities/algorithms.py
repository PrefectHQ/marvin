import heapq
from typing import List

import numpy as np


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Calculate cosine similarity with numpy."""
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def max_marginal_relevance(
    query_embedding: np.ndarray,
    embedding_list: list,
    lambda_mult: float = 0.5,
    k: int = 2,
) -> List[int]:
    """Return document indices of maximally marginal relevance.

    See https://www.cs.cmu.edu/~jgc/publication/The_Use_MMR_Diversity_Based_LTMIR_1998.pdf
    """  # noqa
    idxs: List[int] = []
    query_norm = np.linalg.norm(query_embedding)
    norms = [np.linalg.norm(emb) for emb in embedding_list]
    max_heap: List[float] = []

    for i, emb in enumerate(embedding_list):
        first_part = np.dot(query_embedding, emb) / (query_norm * norms[i])
        second_part = (
            max(cosine_similarity(emb, embedding_list[j]) for j in idxs)
            if idxs
            else 0.0
        )
        equation_score = lambda_mult * first_part - (1 - lambda_mult) * second_part

        if len(max_heap) < k:
            heapq.heappush(max_heap, (-equation_score, i))
        elif -equation_score > max_heap[0][0]:
            heapq.heappushpop(max_heap, (-equation_score, i))

    return [idx for _, idx in sorted(max_heap, reverse=True)]
