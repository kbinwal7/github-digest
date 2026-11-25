"""Small, dependency-free retrieval metrics used by the evaluation runner."""
import math

def recall_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    if not relevant: return 0.0
    return len(set(retrieved[:k]) & relevant) / len(relevant)

def reciprocal_rank(retrieved: list[str], relevant: set[str]) -> float:
    for rank,item in enumerate(retrieved,1):
        if item in relevant: return 1.0/rank
    return 0.0

def ndcg_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    dcg=sum((1.0/math.log2(rank+1)) for rank,item in enumerate(retrieved[:k],1) if item in relevant)
    ideal=sum(1.0/math.log2(rank+1) for rank in range(1,min(len(relevant),k)+1))
    return dcg/ideal if ideal else 0.0
