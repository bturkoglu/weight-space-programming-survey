"""Arm B2: mechanical direction ablation (no LLM, no human choice). Fixed pipeline (PROTOCOL AMENDMENT-2):
  splits : fixed-seed split of MATH train practice problems into DIR (512), DEV (256), HOLD (256)
  gen    : vLLM practice answers, MIT sampling, 8,192-token proxy budget, 1 sample/problem; label finished (EOS) vs
           not finished (cut at budget), plus loop onset (first repeated 64-token window) for description
  read   : teacher-forced read (HF, fp16) of DIR answers; per layer l (output of layer l, l = 0..L-2) mean residual over
           answer tokens of not-finished answers minus finished answers -> diff_l
  build  : top-k layers by ||diff_l||; for each, u = diff_l/||diff_l|| and W' = W - alpha u u^T W on that layer's two
           residual-writing matrices (mlp.down_proj and linear_attn.out_proj / self_attn.o_proj)
  score  : paired comparison of candidate vs unedited on a split -> acc gain, finish-rate gain
Usage:
  b2.py splits
  b2.py gen   --model DIR --split dir|dev|hold --out OUTDIR [--shard i --nshards n] [--save_ids]
  b2.py read  --gen OUTDIR --out results/b2/dirs.pt
  b2.py build --dirs PT --k K --alpha A --out MODELDIR
  b2.py score --base OUTDIR --cand OUTDIR [OUTDIR ...]"""
import argparse, glob, json, os, random, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
BASE_DIR = os.path.join(ROOT, "models", "Qwen3.5-0.8B")
PRACTICE = os.path.join(ROOT, "data", "practice", "math_train.jsonl")
SPLITS = os.path.join(ROOT, "data", "b2_splits.json")
INSTR = "Please reason step by step, and put your final answer within \\boxed{}."
SEED_SPLIT, N_DIR, N_DEV, N_HOLD, W = 20261117, 512, 256, 256, 64


def loop_onset(ids, w=W):
    seen = set()
    for i in range(0, len(ids) - w + 1):
        h = hash(tuple(ids[i:i + w]))
        if h in seen: return i
        seen.add(h)
    return None


def cmd_splits(a):
    rows = [json.loads(l) for l in open(PRACTICE)]
    ids = sorted(r["id"] for r in rows); random.Random(SEED_SPLIT).shuffle(ids)
    sp = {"dir": ids[:N_DIR], "dev": ids[N_DIR:N_DIR + N_DEV], "hold": ids[N_DIR + N_DEV:N_DIR + N_DEV + N_HOLD],
          "seed": SEED_SPLIT, "source": "practice/math_train.jsonl"}
    json.dump(sp, open(SPLITS, "w"), indent=0); print({k: len(v) for k, v in sp.items() if isinstance(v, list)})


def cmd_gen(a):
    from vllm import LLM, SamplingParams
    from eval_vllm import grade, last_boxed
    prob = {}
    for l in open(PRACTICE):
        r = json.loads(l); prob[r["id"]] = r
    ids = json.load(open(SPLITS))[a.split][a.shard::a.nshards]
    os.makedirs(a.out, exist_ok=True); path = os.path.join(a.out, f"gen_shard{a.shard}of{a.nshards}.jsonl")
    if os.path.exists(path):
        done = {json.loads(l)["id"] for l in open(path)}; ids = [i for i in ids if i not in done]
    if not ids: print("nothing to do"); return
    llm = LLM(model=a.model, dtype="float16", seed=a.seed, max_model_len=a.maxtok + 1024, gpu_memory_utilization=0.9,
              enable_prefix_caching=True, limit_mm_per_prompt={"image": 0, "video": 0})
    tok = llm.get_tokenizer()
    sp = SamplingParams(n=1, temperature=0.6, top_p=0.95, top_k=20, presence_penalty=1.5, max_tokens=a.maxtok,
                        seed=a.seed)
    step = 32
    for c0 in range(0, len(ids), step):
        part = ids[c0:c0 + step]
        prompts = [tok.apply_chat_template([{"role": "user", "content": prob[i]["problem"] + "\n" + INSTR}],
                                           tokenize=False, add_generation_prompt=True, enable_thinking=True)
                   for i in part]
        t0 = time.time(); outs = llm.generate(prompts, sp); dt = time.time() - t0; nt = 0
        with open(path, "a") as f:
            for i, o in zip(part, outs):
                c = o.outputs[0]; tid = list(c.token_ids); nt += len(tid)
                fin = c.finish_reason == "stop"
                rec = {"id": i, "correct": grade(last_boxed(c.text), prob[i]["answer"]), "n_tokens": len(tid),
                       "finished": fin, "loop_at": None if fin else loop_onset(tid)}
                if a.save_ids: rec["token_ids"] = tid
                f.write(json.dumps(rec) + "\n")
        print(f"chunk {c0 // step + 1}: {len(part)} answers {nt} tokens {dt:.0f}s {nt / dt:.0f} tok/s", flush=True)


def load_gen(d):
    return {r["id"]: r for f in sorted(glob.glob(os.path.join(d, "gen_shard*.jsonl"))) for r in map(json.loads, open(f))}


def cmd_read(a):
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM
    prob = {}
    for l in open(PRACTICE):
        r = json.loads(l); prob[r["id"]] = r
    G = load_gen(a.gen)
    tok = AutoTokenizer.from_pretrained(BASE_DIR)
    m = AutoModelForCausalLM.from_pretrained(BASE_DIR, dtype=torch.float16).to("cuda").eval()
    L = m.config.text_config.num_hidden_layers if hasattr(m.config, "text_config") else m.config.num_hidden_layers
    H = m.config.text_config.hidden_size if hasattr(m.config, "text_config") else m.config.hidden_size
    acc = {True: torch.zeros(L - 1, H, dtype=torch.float64), False: torch.zeros(L - 1, H, dtype=torch.float64)}
    cnt = {True: 0, False: 0}; t0 = time.time()
    for n, (i, r) in enumerate(sorted(G.items())):
        pre = tok.apply_chat_template([{"role": "user", "content": prob[i]["problem"] + "\n" + INSTR}], tokenize=False,
                                      add_generation_prompt=True, enable_thinking=True)
        pids = tok(pre, add_special_tokens=False).input_ids; aids = r["token_ids"][:a.maxread]
        if len(aids) <= 2 * W: continue
        x = torch.tensor([pids + aids], device="cuda")
        with torch.no_grad():
            hs = m(x, output_hidden_states=True).hidden_states  # hs[l+1] = output of layer l; hs[L] is post-norm
        a0 = len(pids) + W
        for l in range(L - 1):
            acc[r["finished"]][l] += hs[l + 1][0, a0:].double().mean(0).cpu()
        cnt[r["finished"]] += 1
        if n % 64 == 0: print(f"read {n}/{len(G)} {time.time() - t0:.0f}s", flush=True)
    diff = acc[False] / cnt[False] - acc[True] / cnt[True]
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    torch.save({"diff": diff, "n_notfinished": cnt[False], "n_finished": cnt[True], "maxread": a.maxread}, a.out)
    print("n_notfinished", cnt[False], "n_finished", cnt[True], "norms", [round(float(v), 2) for v in diff.norm(dim=1)])


def cmd_build(a):
    import torch
    from safetensors import safe_open
    from safetensors.torch import save_file
    D = torch.load(a.dirs)["diff"]; norms = D.norm(dim=1)
    layers = sorted(torch.argsort(norms, descending=True)[:a.k].tolist())
    st = os.path.join(BASE_DIR, "model.safetensors-00001-of-00001.safetensors")
    os.makedirs(a.out, exist_ok=True)
    for f in os.listdir(BASE_DIR):
        if not f.endswith(".safetensors") and not os.path.exists(os.path.join(a.out, f)):
            os.symlink(os.path.abspath(os.path.join(BASE_DIR, f)), os.path.join(a.out, f))
    T = {}; edited = []
    with safe_open(st, "pt") as f:
        meta = f.metadata() or {}
        for k in f.keys(): T[k] = f.get_tensor(k)
    for l in layers:
        u = (D[l] / D[l].norm()).double()
        for k in (f"model.language_model.layers.{l}.mlp.down_proj.weight",
                  f"model.language_model.layers.{l}.linear_attn.out_proj.weight",
                  f"model.language_model.layers.{l}.self_attn.o_proj.weight"):
            if k in T:
                w = T[k].double(); T[k] = (w - a.alpha * torch.outer(u, u @ w)).to(T[k].dtype); edited.append(k)
    save_file(T, os.path.join(a.out, os.path.basename(st)),
              metadata={**meta, "format": "pt", "b2": json.dumps({"k": a.k, "alpha": a.alpha, "layers": layers})})
    json.dump({"k": a.k, "alpha": a.alpha, "layers": layers, "tensors": edited}, open(os.path.join(a.out, "b2_edit.json"), "w"))
    print("built", a.out, "layers", layers, "tensors", len(edited))


def cmd_score(a):
    B = load_gen(a.base); out = []
    for c in a.cand:
        C = load_gen(c); ids = sorted(set(B) & set(C))
        g = [C[i]["correct"] - B[i]["correct"] for i in ids]; fz = [C[i]["finished"] - B[i]["finished"] for i in ids]
        out.append({"cand": c, "n": len(ids), "acc_base": sum(B[i]["correct"] for i in ids) / len(ids),
                    "acc": sum(C[i]["correct"] for i in ids) / len(ids), "gain": sum(g) / len(ids),
                    "finish_gain": sum(fz) / len(ids)})
    out.sort(key=lambda r: (-r["gain"], -r["finish_gain"]))
    for r in out: print(json.dumps(r))
    if a.json: json.dump(out, open(a.json, "w"), indent=1)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd")
    ap.add_argument("--model"); ap.add_argument("--split"); ap.add_argument("--out"); ap.add_argument("--gen")
    ap.add_argument("--dirs"); ap.add_argument("--k", type=int); ap.add_argument("--alpha", type=float)
    ap.add_argument("--base"); ap.add_argument("--cand", nargs="*"); ap.add_argument("--json")
    ap.add_argument("--shard", type=int, default=0); ap.add_argument("--nshards", type=int, default=1)
    ap.add_argument("--seed", type=int, default=0); ap.add_argument("--maxtok", type=int, default=8192)
    ap.add_argument("--maxread", type=int, default=4096); ap.add_argument("--save_ids", action="store_true")
    a = ap.parse_args(); globals()["cmd_" + a.cmd](a)
