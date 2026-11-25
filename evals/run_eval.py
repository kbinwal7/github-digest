"""Evaluate saved retrieval runs. Input JSON: [{query, relevant_ids, retrieved_ids, latency_ms}]."""
import argparse,csv,json,statistics
from pathlib import Path
from evals.metrics import recall_at_k,reciprocal_rank,ndcg_at_k

def evaluate(rows):
    if not rows: raise ValueError("Evaluation dataset is empty")
    result={"queries":len(rows)}
    for k in (1,3,5,10):
        result[f"recall@{k}"]=statistics.mean(recall_at_k(r["retrieved_ids"],set(r["relevant_ids"]),k) for r in rows)
        result[f"ndcg@{k}"]=statistics.mean(ndcg_at_k(r["retrieved_ids"],set(r["relevant_ids"]),k) for r in rows)
    result["mrr"]=statistics.mean(reciprocal_rank(r["retrieved_ids"],set(r["relevant_ids"])) for r in rows)
    lat=sorted(r["latency_ms"] for r in rows if "latency_ms" in r)
    if lat:
        result["latency_p50_ms"]=lat[int(.50*(len(lat)-1))]
        result["latency_p95_ms"]=lat[int(.95*(len(lat)-1))]
    return result

if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("input",type=Path);parser.add_argument("--out",type=Path,default=Path("evals/results"))
    args=parser.parse_args();rows=json.loads(args.input.read_text());result=evaluate(rows)
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"summary.json").write_text(json.dumps(result,indent=2))
    with (args.out/"summary.csv").open("w",newline="") as f:
        w=csv.writer(f);w.writerow(["metric","value"]);w.writerows(result.items())
    print(json.dumps(result,indent=2))
