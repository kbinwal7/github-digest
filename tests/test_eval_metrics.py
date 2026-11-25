from evals.metrics import recall_at_k, reciprocal_rank, ndcg_at_k
from evals.run_eval import evaluate

def test_retrieval_metrics():
    ids=["a","b","c"]; relevant={"b","c"}
    assert recall_at_k(ids,relevant,2)==0.5
    assert reciprocal_rank(ids,relevant)==0.5
    assert 0 < ndcg_at_k(ids,relevant,3) <= 1

def test_eval_latency_and_metrics():
    result=evaluate([{"retrieved_ids":["a"],"relevant_ids":["a"],"latency_ms":10},
                     {"retrieved_ids":[],"relevant_ids":["b"],"latency_ms":20}])
    assert result["queries"]==2 and result["mrr"]==0.5
    assert result["latency_p50_ms"]==10 and result["latency_p95_ms"]==10
