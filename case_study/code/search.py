"""Arms B3 (random search) and B4 (evolution strategy on B2 directions). PROTOCOL AMENDMENT-3. Runs on the TRUBA UI
node as a light orchestrator (builds candidate checkpoints on CPU, submits GPU array jobs, waits, scores, selects).
Edit family (both arms): for layer l, unit direction u in residual space, strength alpha:
  W' = W - alpha u u^T W  on mlp.down_proj and the attention output matrix of layer l (as B2).
B3: candidate = random layer set (size k uniform in {1,2,4,8} from layers 0..22), Gaussian unit direction per layer,
    alpha uniform in {0.5,1,2}. 22 candidates on DEV, top 2 on HOLD.
B4: genome = alpha_l in [0,1] for l = 0..22 on the B2 directions (results/b2/dirs.pt, no new passes). Generation 0 =
    B2 winner genome (alpha 0.5 on its 8 layers) + 4 mutants; generations 1-3: 5 children each from the 2 best
    candidates evaluated so far (uniform crossover, then per-layer Gaussian mutation sd 0.15 with prob 0.3, clip [0,1]).
    20 candidates on DEV, top 2 on HOLD. B4 total incl. B2's 21 passes = 21 + 0.5 + 20 + 0.5 + 2 = 44 <= 50.
Proxy: 16,384 tokens, 1 sample, paired with unedited answers on the same split. Score = d_acc + 0.25 * d_finish.
Submitted edit = best HOLD score; evaluated on first-50 MATH-500 x 4 at 32,768 tokens.
Usage: python code/search.py --arm b3|b4 --seed S"""
import argparse, json, os, random, subprocess, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from b2 import load_gen, BASE_DIR
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
L, H, MAXTOK = 23, 1024, 16384
RES = os.path.join(ROOT, "results", "search")


def log(*a):
    print(time.strftime("%m-%d %H:%M"), *a, flush=True)


def build(spec, out):
    """spec = {"edits": [{"layer": l, "dir": "b2" | "rand:<int>", "alpha": a}, ...]}"""
    import torch
    from safetensors import safe_open
    from safetensors.torch import save_file
    if os.path.exists(os.path.join(out, "spec.json")): return
    D = torch.load(os.path.join(ROOT, "results", "b2", "dirs.pt"))["diff"]
    st = os.path.join(BASE_DIR, "model.safetensors-00001-of-00001.safetensors")
    os.makedirs(out, exist_ok=True)
    for f in os.listdir(BASE_DIR):
        if not f.endswith(".safetensors") and not os.path.exists(os.path.join(out, f)):
            os.symlink(os.path.abspath(os.path.join(BASE_DIR, f)), os.path.join(out, f))
    T = {}
    with safe_open(st, "pt") as f:
        meta = f.metadata() or {}
        for k in f.keys(): T[k] = f.get_tensor(k)
    for e in spec["edits"]:
        if e["alpha"] == 0: continue
        l = e["layer"]
        if e["dir"] == "b2": u = D[l].double()
        else:
            g = torch.Generator().manual_seed(int(e["dir"].split(":")[1])); u = torch.randn(H, generator=g, dtype=torch.float64)
        u = u / u.norm()
        for k in (f"model.language_model.layers.{l}.mlp.down_proj.weight",
                  f"model.language_model.layers.{l}.linear_attn.out_proj.weight",
                  f"model.language_model.layers.{l}.self_attn.o_proj.weight"):
            if k in T:
                w = T[k].double(); T[k] = (w - e["alpha"] * torch.outer(u, u @ w)).to(T[k].dtype)
    save_file(T, os.path.join(out, os.path.basename(st)), metadata={**meta, "format": "pt", "spec": json.dumps(spec)})
    json.dump(spec, open(os.path.join(out, "spec.json"), "w"))
    for f in os.listdir(out):
        if f.startswith(".tmp"): os.remove(os.path.join(out, f))


def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=ROOT).stdout.strip()


def run_gen(names, split):
    """names: candidate names (model dir models/search/<name>) or 'base'. 2 shards each. Blocks until done;
    resubmits once for unfinished work (gen is resumable)."""
    for attempt in range(2):
        todo = [n for n in names if not done(n, split)]
        if not todo: return
        while True:  # per-user submit limit (QOS normal: 100 jobs) -> wait and retry until accepted
            jid = sh(f'sbatch --parsable --array=0-{2 * len(todo) - 1} --export=ALL,SPLIT={split},LIST="{" ".join(todo)}",'
                     f'MAXTOK={MAXTOK} truba/search_cand.sbatch')
            if jid.strip().split(";")[0].isdigit(): break
            log("sbatch refused, retrying in 10 min"); time.sleep(600)
        log(f"submitted {jid}: {len(todo)} x {split} (attempt {attempt + 1})")
        while sh(f"squeue -h -j {jid} | wc -l") not in ("0", ""):
            time.sleep(600)
    left = [n for n in names if not done(n, split)]
    if left: log("INCOMPLETE after retry:", left)


def gen_dir(n, split): return os.path.join(RES, f"gen_{n}_{split}")


def n_split(split): return len(json.load(open(os.path.join(ROOT, "data", "b2_splits.json")))[split])


def done(n, split):
    d = gen_dir(n, split)
    return os.path.isdir(d) and len(load_gen(d)) >= n_split(split)


def score(n, split):
    B, C = load_gen(gen_dir("base", split)), load_gen(gen_dir(n, split)); ids = sorted(set(B) & set(C))
    da = sum(C[i]["correct"] - B[i]["correct"] for i in ids) / len(ids)
    df = sum(C[i]["finished"] - B[i]["finished"] for i in ids) / len(ids)
    return {"name": n, "split": split, "n": len(ids), "d_acc": da, "d_finish": df, "score": da + 0.25 * df,
            "acc": sum(C[i]["correct"] for i in ids) / len(ids)}


def request(spec, out):
    """Write the build request only; the GPU job builds it (UI node has a 300 s CPU-time limit per process)."""
    os.makedirs(out, exist_ok=True)
    if not os.path.exists(os.path.join(out, "spec.json")): json.dump(spec, open(os.path.join(out, "spec_req.json"), "w"))


def evaluate(specs, split):
    for n, s in specs.items(): request(s, os.path.join(ROOT, "models", "search", n))
    run_gen(list(specs), split)
    return [score(n, split) for n in specs if done(n, split)]


def b3_specs(rng, n0, count):
    out = {}
    for j in range(count):
        k = rng.choice([1, 2, 4, 8]); layers = sorted(rng.sample(range(L), k)); a = rng.choice([0.5, 1, 2])
        out[f"b3s{n0}_{j:02d}"] = {"edits": [{"layer": l, "dir": f"rand:{rng.randrange(1 << 30)}", "alpha": a} for l in layers]}
    return out


def genome_spec(g): return {"edits": [{"layer": l, "dir": "b2", "alpha": round(a, 4)} for l, a in enumerate(g) if a > 0]}


def mutate(rng, g):
    return [min(1.0, max(0.0, a + rng.gauss(0, 0.15))) if rng.random() < 0.3 else a for a in g]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--arm"); ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--build"); a = ap.parse_args()
    if a.build:
        build(json.load(open(os.path.join(a.build, "spec_req.json"))), a.build); return
    rng = random.Random(1000 * a.seed + (3 if a.arm == "b3" else 4))
    os.makedirs(RES, exist_ok=True); tag = f"{a.arm}_seed{a.seed}"; rec_path = os.path.join(RES, f"{tag}.json")
    if a.arm == "base":
        run_gen(["base"], "dev"); run_gen(["base"], "hold"); log("base done"); return
    log("start", tag)
    while not (done("base", "dev") and done("base", "hold")):
        time.sleep(600)
    scored = []
    if a.arm == "b3":
        scored = evaluate(b3_specs(rng, a.seed, 22), "dev")
    else:
        g0 = [0.5 if l in (15, 16, 17, 18, 19, 20, 21, 22) else 0.0 for l in range(L)]
        genomes = {f"b4s{a.seed}_g0_00": g0}
        for j in range(1, 5): genomes[f"b4s{a.seed}_g0_{j:02d}"] = mutate(rng, g0)
        for gen in range(4):
            if gen > 0:
                best = sorted(scored, key=lambda r: -r["score"])[:2]; P = [genomes[b["name"]] for b in best]
                for j in range(5):
                    child = [rng.choice([P[0][l], P[1][l]]) for l in range(L)]
                    genomes[f"b4s{a.seed}_g{gen}_{j:02d}"] = mutate(rng, child)
            new = {n: genome_spec(g) for n, g in genomes.items() if n.startswith(f"b4s{a.seed}_g{gen}_")}
            scored += evaluate(new, "dev"); log("gen", gen, "best", max(scored, key=lambda r: r["score"]))
            json.dump({"dev": scored, "genomes": genomes}, open(rec_path, "w"), indent=1)
    top = [r["name"] for r in sorted(scored, key=lambda r: -r["score"])[:2]]
    specs = {n: json.load(open(os.path.join(ROOT, "models", "search", n, "spec.json"))) for n in top}  # built during DEV
    hold = evaluate(specs, "hold"); best = max(hold, key=lambda r: r["score"])["name"]
    json.dump({"dev": scored, "hold": hold, "submitted": best, **({"genomes": genomes} if a.arm == "b4" else {})},
              open(rec_path, "w"), indent=1)
    log("submitted", best, hold)
    while True:
        jid = sh(f"sbatch --parsable --export=ALL,MODEL=models/search/{best},TAG={tag}_{best} truba/eval_model.sbatch")
        if jid.strip().split(";")[0].isdigit(): break
        log("sbatch refused, retrying in 10 min"); time.sleep(600)
    log("final eval job", jid)


if __name__ == "__main__":
    main()
