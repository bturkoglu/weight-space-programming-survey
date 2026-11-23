"""MIT 'think35' evaluation re-implemented (own code): vLLM, chat template with thinking, prompt = problem + "\\n" +
INSTR, T 0.6, top_p 0.95, top_k 20, presence penalty 1.5, max 32,768 new tokens; grade the LAST \\boxed{} with
math-verify against \\boxed{gold}. Writes per-problem results and a summary (acc, cut_share, mean_tokens).
Usage: eval_vllm.py --model DIR --data math500.jsonl --samples 4 --out OUT_DIR [--dtype float16] [--limit N] [--seed 0]
data rows: {"id", "problem", "answer"}."""
import argparse, json, os, time

def last_boxed(s):
    i = max(s.rfind("\\boxed"), s.rfind("\\fbox"))
    if i < 0: return None
    j = s.find("{", i)
    if j < 0:
        rest = s[i + len("\\boxed"):].strip()
        return rest.split("$")[0].split("\n")[0].strip() or None
    depth = 0
    for k in range(j, len(s)):
        if s[k] == "{": depth += 1
        elif s[k] == "}":
            depth -= 1
            if depth == 0: return s[j + 1:k]
    return None

def grade(pred, gold):
    if pred is None: return 0
    from math_verify import parse, verify
    try: return int(bool(verify(parse("\\boxed{" + gold + "}"), parse("\\boxed{" + pred + "}"))))
    except Exception: return 0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model"); ap.add_argument("--data"); ap.add_argument("--out"); ap.add_argument("--samples", type=int, default=4)
    ap.add_argument("--dtype", default="bfloat16"); ap.add_argument("--limit", type=int, default=0); ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--max_tokens", type=int, default=32768); ap.add_argument("--max_model_len", type=int, default=34816)
    ap.add_argument("--shard", type=int, default=0); ap.add_argument("--nshards", type=int, default=1)
    ap.add_argument("--presence", type=float, default=1.5); ap.add_argument("--repetition", type=float, default=1.0)
    ap.add_argument("--no_thinking", action="store_true", help="B1c: chat template with enable_thinking=False")
    ap.add_argument("--max_num_seqs", type=int, default=0, help="vLLM concurrency cap; speed only")
    ap.add_argument("--chunk", type=int, default=0, help="problems per chunk; results are appended after each chunk")
    a = ap.parse_args()
    from vllm import LLM, SamplingParams
    rows = [json.loads(l) for l in open(a.data)]
    if a.limit: rows = rows[:a.limit]
    rows = rows[a.shard::a.nshards]
    os.makedirs(a.out, exist_ok=True)
    tag = f"shard{a.shard}of{a.nshards}"
    res_path = os.path.join(a.out, f"samples_{tag}.jsonl"); txt_path = os.path.join(a.out, f"first_samples_{tag}.jsonl")
    done = set()
    if os.path.exists(res_path):  # resume: skip problems already written
        done = {json.loads(l)["id"] for l in open(res_path)}
    rows = [r for r in rows if r["id"] not in done]
    llm = LLM(model=a.model, dtype=a.dtype, seed=a.seed, max_model_len=a.max_model_len, gpu_memory_utilization=0.9,
              enable_prefix_caching=True,
              **({"max_num_seqs": a.max_num_seqs} if a.max_num_seqs else {}),
              limit_mm_per_prompt={"image": 0, "video": 0})  # text-only; skips the vision-encoder profiling
    tok = llm.get_tokenizer()
    INSTR = "Please reason step by step, and put your final answer within \\boxed{}."
    sp = SamplingParams(n=a.samples, temperature=0.6, top_p=0.95, top_k=20, presence_penalty=a.presence,
                        repetition_penalty=a.repetition, max_tokens=a.max_tokens, seed=a.seed)
    step = a.chunk or len(rows) or 1
    for c0 in range(0, len(rows), step):
        part = rows[c0:c0 + step]
        prompts = [tok.apply_chat_template([{"role": "user", "content": r["problem"] + "\n" + INSTR}], tokenize=False,
                                           add_generation_prompt=True, enable_thinking=not a.no_thinking) for r in part]
        t0 = time.time(); outs = llm.generate(prompts, sp); dt = time.time() - t0
        ntok = 0
        with open(res_path, "a") as fr, open(txt_path, "a") as fs:
            for r, o in zip(part, outs):
                recs = []
                for k, c in enumerate(o.outputs):
                    n = len(c.token_ids); ntok += n
                    recs.append({"k": k, "correct": grade(last_boxed(c.text), r["answer"]), "tokens": n,
                                 "cut": c.finish_reason == "length"})
                    if k == 0: fs.write(json.dumps({"id": r["id"], "answer": r["answer"], "text": c.text}) + "\n")
                fr.write(json.dumps({"id": r["id"], "samples": recs, "chunk_seconds": dt}) + "\n")
        print(f"[{tag}] chunk {c0 // step + 1}: {len(part)} problems, {ntok} tokens, {dt:.0f}s, {ntok / dt:.0f} tok/s",
              flush=True)

if __name__ == "__main__":
    main()
