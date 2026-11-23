"""Grade AMENDMENT-6 texts. MMLU-Pro: official TIGER-Lab extraction (answer is (X) -> Answer: X -> last lone letter)
on the text after the last </think> (whole text if none). IFEval: strict prompt-level with the official
google-research instruction_following_eval checkers (path given by --ifeval_lib) on the text after the last </think>;
empty response if there is no </think> (as MIT). Writes results/other_<set>_<tag>/graded.json and prints a table with
paired differences (per-item mean over samples; bootstrap over items, 10,000 resamples, seed 0).
Usage: grade_other.py --ifeval_lib DIR --tags unedited p50c b2 b4s0 b4s1"""
import argparse, glob, json, os, random, re, sys

def mmlu_extract(text):
    m = re.search(r"answer is \(?([A-J])\)?", text)
    if m: return m.group(1)
    # same results as the official r".*[aA]nswer:\s*([A-J])" (first line with a match, last match on it) and
    # r"\b[A-J]\b(?!.*\b[A-J]\b)" with DOTALL (last lone letter), without their quadratic backtracking on long loops
    for line in text.split("\n"):
        ms = re.findall(r"[aA]nswer:\s*([A-J])", line)
        if ms: return ms[-1]
    ms = re.findall(r"\b[A-J]\b", text)
    return ms[-1] if ms else None

def after_think(t, empty_if_none):
    return t.split("</think>")[-1].strip() if "</think>" in t else ("" if empty_if_none else t)

def ifeval_ok(IR, r, resp):
    if not resp.strip(): return 0
    for iid, kw in zip(r["instruction_id_list"], r["kwargs"]):
        ins = IR.INSTRUCTION_DICT[iid](iid)
        ins.build_description(**{k: v for k, v in (kw or {}).items() if v is not None})
        args = ins.get_instruction_args()
        if args and "prompt" in args: ins.build_description(prompt=r["prompt"])
        if not ins.check_following(resp): return 0
    return 1

def boot(g):
    rng = random.Random(0); bs = sorted(sum(rng.choice(g) for _ in g) / len(g) for _ in range(10000))
    return round(sum(g) / len(g), 3), [round(bs[249], 3), round(bs[9749], 3)]

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--ifeval_lib"); ap.add_argument("--tags", nargs="+"); a = ap.parse_args()
    sys.path.insert(0, a.ifeval_lib); from instruction_following_eval import instructions_registry as IR
    data = {s: {json.loads(l)["id"]: json.loads(l) for l in open(f"data/other/{s}.jsonl")} for s in ("mmlupro1k", "ifeval")}
    per = {}
    for s in ("mmlupro1k", "ifeval"):
        for t in a.tags:
            d = f"results/other_{s}_{t}"
            if not os.path.isdir(d): continue
            rows = [json.loads(l) for f in sorted(glob.glob(f"{d}/texts_shard*.jsonl")) for l in open(f)]
            P, cut, ntok, n = {}, 0, 0, 0
            for r in rows:
                it = data[s][r["id"]]; sc = []
                for x in r["samples"]:
                    n += 1; cut += x["cut"]; ntok += x["tokens"]
                    if s == "mmlupro1k": sc.append(int(mmlu_extract(after_think(x["text"], False)) == it["answer"]))
                    else: sc.append(ifeval_ok(IR, it, after_think(x["text"], True)))
                P[r["id"]] = sum(sc) / len(sc)
            per[(s, t)] = P
            summ = {"set": s, "tag": t, "items": len(P), "acc": round(sum(P.values()) / max(len(P), 1), 4),
                    "cut_share": round(cut / max(n, 1), 4), "mean_tokens": round(ntok / max(n, 1))}
            json.dump({"summary": summ, "per_item": P}, open(f"{d}/graded.json", "w")); print(json.dumps(summ))
        for ref in ("unedited", "p50c"):
            if (s, ref) not in per: continue
            for t in a.tags:
                if t == ref: continue
                B, C = per[(s, ref)], per[(s, t)]; ids = sorted(set(B) & set(C)); g = [C[i] - B[i] for i in ids]
                if g: print(json.dumps({"set": s, "cand": t, "vs": ref, "n": len(ids), "diff_ci95": boot(g),
                                        "up": sum(x > 0 for x in g), "down": sum(x < 0 for x in g)}))

if __name__ == "__main__":
    main()
