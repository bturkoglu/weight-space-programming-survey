"""Merge samples_shard*.jsonl of one eval dir into summary.json (acc, cut_share, mean_tokens, n)."""
import glob, json, sys
d = sys.argv[1]; rows = [json.loads(l) for f in sorted(glob.glob(f"{d}/samples_shard*.jsonl")) for l in open(f)]
S = [s for r in rows for s in r["samples"]]
summ = {"problems": len(rows), "answers": len(S), "acc": sum(s["correct"] for s in S) / max(len(S), 1),
        "cut_share": sum(s["cut"] for s in S) / max(len(S), 1), "mean_tokens": sum(s["tokens"] for s in S) / max(len(S), 1)}
json.dump(summ, open(f"{d}/summary.json", "w"), indent=1); print(json.dumps(summ))
