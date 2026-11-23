"""PROTOCOL AMENDMENT-6: MMLU-Pro (MIT's fixed 1,000 items, 1 sample) and IFEval (MIT's 541 items, 2 samples), think35
sampling as in eval_vllm.py (T 0.6, top_p 0.95, top_k 20, presence 1.5, 32,768 new tokens, thinking on, fp16).
Generation only; texts are graded afterwards by code/grade_other.py.
MMLU-Pro prompt: the official MMLU-Pro zero-shot chain-of-thought format (TIGER-Lab evaluate_from_api.py without the
5 examples). IFEval prompt: the IFEval prompt as the user turn.
Usage: eval_other.py --model DIR --set mmlupro1k|ifeval --out DIR --shard i --nshards n"""
import argparse, json, os, time

def mmlu_prompt(r):
    opts = "\n".join(f"{'ABCDEFGHIJ'[i]}. {o}" for i, o in enumerate(r["options"]))
    return (f"The following are multiple choice questions (with answers) about {r['category']}. Think step by step and "
            f"then finish your answer with \"the answer is (X)\" where X is the correct letter choice.\n\n"
            f"Question: {r['question']}\nOptions:\n{opts}\nAnswer: Let's think step by step.")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model"); ap.add_argument("--set"); ap.add_argument("--out")
    ap.add_argument("--shard", type=int, default=0); ap.add_argument("--nshards", type=int, default=1)
    ap.add_argument("--chunk", type=int, default=25); ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    from vllm import LLM, SamplingParams
    rows = [json.loads(l) for l in open(f"data/other/{a.set}.jsonl")][a.shard::a.nshards]
    os.makedirs(a.out, exist_ok=True); path = os.path.join(a.out, f"texts_shard{a.shard}of{a.nshards}.jsonl")
    if os.path.exists(path):
        done = {json.loads(l)["id"] for l in open(path)}; rows = [r for r in rows if r["id"] not in done]
    if not rows: print("nothing to do"); return
    llm = LLM(model=a.model, dtype="float16", seed=a.seed, max_model_len=34816, gpu_memory_utilization=0.9,
              enable_prefix_caching=True, limit_mm_per_prompt={"image": 0, "video": 0})
    tok = llm.get_tokenizer()
    sp = SamplingParams(n=1 if a.set == "mmlupro1k" else 2, temperature=0.6, top_p=0.95, top_k=20, presence_penalty=1.5,
                        max_tokens=32768, seed=a.seed)
    for c0 in range(0, len(rows), a.chunk):
        part = rows[c0:c0 + a.chunk]
        prompts = [tok.apply_chat_template([{"role": "user", "content": mmlu_prompt(r) if a.set == "mmlupro1k" else r["prompt"]}],
                                           tokenize=False, add_generation_prompt=True, enable_thinking=True) for r in part]
        t0 = time.time(); outs = llm.generate(prompts, sp); dt = time.time() - t0; nt = 0
        with open(path, "a") as f:
            for r, o in zip(part, outs):
                s = [{"text": c.text, "tokens": len(c.token_ids), "cut": c.finish_reason == "length"} for c in o.outputs]
                nt += sum(x["tokens"] for x in s); f.write(json.dumps({"id": r["id"], "samples": s}) + "\n")
        print(f"chunk {c0 // a.chunk + 1}: {len(part)} items {nt} tokens {dt:.0f}s {nt / dt:.0f} tok/s", flush=True)

if __name__ == "__main__":
    main()
