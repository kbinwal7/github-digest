# Evaluation datasets

Place frozen issue snapshots and manually labelled query sets here. A retrieval run should be serialized as a JSON array of objects with:

```json
[
  {
    "query": "Where is retry behavior implemented?",
    "relevant_ids": ["owner/repo#42"],
    "retrieved_ids": ["owner/repo#42", "owner/repo#18"],
    "latency_ms": 84.2
  }
]
```

The starter repository does not contain real GitHub issue snapshots or human-labelled relevance judgments. Do not treat synthetic labels as ground truth. Build a small labelled set (roughly 40 queries across several repositories) before drawing conclusions. The metrics runner reports Recall@k, MRR, nDCG@k and latency percentiles.
