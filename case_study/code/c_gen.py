"""Arm C (AMENDMENT-7): practice traces for training.
  c_gen.py problems                       -> data/c_problems.json (2,000 ids from MATH train minus B2 DEV/HOLD)
  c_gen.py gen --model DIR --samples n --out OUTDIR --shard i --nshards m   (think35, thinking on, 16,384 tokens)
  c_gen.py build --gen OUTDIR --model DIR --out data/c_train_X.jsonl     (finished, correct, <= 8,192 tokens, 1/problem)
Records: {"id", "k", "text", "n_tokens", "finished", "correct"}. Resumable per chunk."""
import argparse, glob, json, os, random, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
PRACTICE = os.path.join(ROOT, "data", "practice", "math_train.jsonl")
SPLITS = os.path.join(ROOT, "data", "b2_splits.json")
PROBS = os.path.join(ROOT, "data", "c_problems.json")
INSTR = "Please reason step by step, and put your final answer within \\boxed{}."
SEED, NP, MAXLEN = 20261122, 2000, 8192


def practice():
    return {r["id"]: r for r in map(json.loads, open(PRACTICE))}


def prompt(tok, problem):
    return tok.apply_chat_template([{"role": "user", "content": problem + "\n" + INSTR}], tokenize=False,
                                   add_generation_prompt=True, enable_thinking=True)


def cmd_problems(a):
    sp = json.load(open(SPLITS)); bad = set(sp["dev"]) | set(sp["hold"])
    pool = sorted(i for i in practice() if i not in bad); random.Random(SEED).shuffle(pool)
    json.dump({"ids": pool[:NP], "seed": SEED, "pool": len(pool), "excluded": "B2 dev+hold"}, open(PROBS, "w"), indent=0)
    print("pool", len(pool), "chosen", NP)


def cmd_gen(a):
    from vllm import LLM, SamplingParams
    from eval_vllm import grade, last_boxed
    P = practice(); ids = json.load(open(PROBS))["ids"][a.shard::a.nshards]
    os.makedirs(a.out, exist_ok=True); path = os.path.join(a.out, f"gen_shard{a.shard}of{a.nshards}.jsonl")
    if os.path.exists(path):
        done = {json.loads(l)["id"] for l in open(path)}; ids = [i for i in ids if i not in done]
    if not ids: print("nothing to do"); return
    llm = LLM(model=a.model, dtype="float16", seed=a.seed, max_model_len=a.maxtok + 1024, gpu_memory_utilization=0.9,
              enable_prefix_caching=True, limit_mm_per_prompt={"image": 0, "video": 0},
              **({"max_num_seqs": a.max_num_seqs} if a.max_num_seqs else {}))
    tok = llm.get_tokenizer()
    sp = SamplingParams(n=a.samples, temperature=0.6, top_p=0.95, top_k=20, presence_penalty=1.5,
                        max_tokens=a.maxtok, seed=a.seed)
    step = a.chunk
    for c0 in range(0, len(ids), step):
        part = ids[c0:c0 + step]; t0 = time.time()
        outs = llm.generate([prompt(tok, P[i]["problem"]) for i in part], sp); dt = time.time() - t0; nt = 0
        with open(path, "a") as f:
            for i, o in zip(part, outs):
                for k, c in enumerate(o.outputs):
                    nt += len(c.token_ids)
                    f.write(json.dumps({"id": i, "k": k, "text": c.text, "n_tokens": len(c.token_ids),
                                        "finished": c.finish_reason == "stop",
                                        "correct": grade(last_boxed(c.text), P[i]["answer"])}) + "\n")
        print(f"chunk {c0 // step + 1}: {len(part)} problems {nt} tokens {dt:.0f}s {nt / dt:.0f} tok/s", flush=True)


def cmd_build(a):
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(a.model); P = practice()
    R = [r for f in sorted(glob.glob(os.path.join(a.gen, "gen_shard*.jsonl"))) for r in map(json.loads, open(f))]
    R.sort(key=lambda r: (r["id"], r["k"])); kept, seen, st = [], set(), {"traces": len(R), "finished": 0, "correct": 0,
                                                                         "too_long": 0}
    for r in R:
        st["finished"] += r["finished"]; st["correct"] += r["finished"] and r["correct"]
        if not (r["finished"] and r["correct"]) or r["id"] in seen: continue
        n = len(tok(prompt(tok, P[r["id"]]["problem"]) + r["text"] + "<|im_end|>", add_special_tokens=False).input_ids)
        if n > MAXLEN: st["too_long"] += 1; continue
        seen.add(r["id"]); kept.append({"id": r["id"], "problem": P[r["id"]]["problem"], "text": r["text"], "len": n})
    st.update(problems=len({r["id"] for r in R}), kept=len(kept),
              mean_len=sum(k["len"] for k in kept) / max(1, len(kept)))
    with open(a.out, "w") as f:
        for k in kept: f.write(json.dumps(k) + "\n")
    json.dump(st, open(a.out.replace(".jsonl", "_stats.json"), "w"), indent=1); print(st)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd"); ap.add_argument("--model"); ap.add_argument("--out")
    ap.add_argument("--gen"); ap.add_argument("--samples", type=int, default=1); ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--maxtok", type=int, default=16384); ap.add_argument("--chunk", type=int, default=25)
    ap.add_argument("--max_num_seqs", type=int, default=0, help="vLLM concurrency cap (speed only; 4B on V100)")
    ap.add_argument("--shard", type=int, default=0); ap.add_argument("--nshards", type=int, default=1)
    a = ap.parse_args(); globals()["cmd_" + a.cmd](a)
