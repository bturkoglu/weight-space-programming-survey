"""Paired per-problem gain of eval dir(s) vs a base eval dir: mean over samples per problem, edited minus base;
95% bootstrap CI over problems (10,000 resamples, seed 0). Usage: paired.py BASE_DIR CAND_DIR [CAND_DIR ...]"""
import glob, json, random, sys


def per_problem(d):
    return {r["id"]: sum(s["correct"] for s in r["samples"]) / len(r["samples"])
            for f in sorted(glob.glob(f"{d}/samples_shard*.jsonl")) for r in map(json.loads, open(f))}


B = per_problem(sys.argv[1])
for c in sys.argv[2:]:
    C = per_problem(c); ids = sorted(set(B) & set(C)); g = [C[i] - B[i] for i in ids]; rng = random.Random(0)
    bs = sorted(sum(rng.choice(g) for _ in g) / len(g) for _ in range(10000))
    print(json.dumps({"cand": c, "n": len(ids), "gain": round(sum(g) / len(g), 3), "ci95": [round(bs[249], 3), round(bs[9749], 3)],
                      "up": sum(x > 0 for x in g), "down": sum(x < 0 for x in g)}))
