"""Arm C (AMENDMENT-7): LoRA fine-tuning of Qwen3.5-0.8B on kept practice traces, then merge into full weights.
Own minimal LoRA (no peft). fp16 frozen base, fp32 LoRA params, fp16 autocast + loss scaling (V100 has no bf16).
Fixed settings: rank 16, scale 2 (alpha 32), q/k/v/o, in_proj_qkv/in_proj_z/out_proj, gate/up/down of all text layers;
loss on answer tokens only; AdamW lr 1e-4, 3% warmup, cosine, 2 epochs, 16 sequences per step, clip 1.0, seed 0.
Checkpoints every 10 optimizer steps (resumable across 4 h jobs); writes the merged model when done.
Usage: c_train.py --data data/c_train_self.jsonl --work results/c/train_self --out models/c_self [--max_steps N]"""
import argparse, json, math, os, random, re, sys, time
import torch, torch.nn as nn
from torch.utils.checkpoint import checkpoint
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
BASE = os.path.join(ROOT, "models", "Qwen3.5-0.8B")
ST = "model.safetensors-00001-of-00001.safetensors"
INSTR = "Please reason step by step, and put your final answer within \\boxed{}."
TARGET = re.compile(r"layers\.(\d+)\.((?:self_attn\.(?:q_proj|k_proj|v_proj|o_proj))|(?:linear_attn\.(?:in_proj_qkv|"
                    r"in_proj_z|out_proj))|(?:mlp\.(?:gate_proj|up_proj|down_proj)))$")
R, SCALE, LR, EPOCHS, BATCH, WARM, CLIP, SEED, CHUNK = 16, 2.0, 1e-4, 2, 16, 0.03, 1.0, 0, 1024


class LoRA(nn.Module):
    def __init__(self, base):
        super().__init__(); self.base = base
        self.A = nn.Parameter(torch.empty(R, base.in_features, dtype=torch.float32, device=base.weight.device))
        self.B = nn.Parameter(torch.zeros(base.out_features, R, dtype=torch.float32, device=base.weight.device))
        nn.init.kaiming_uniform_(self.A, a=math.sqrt(5))

    def forward(self, x):
        return self.base(x) + ((x.float() @ self.A.t()) @ self.B.t() * SCALE).to(x.dtype)


def wrap(m):
    names = []
    for name, mod in list(m.named_modules()):
        if "visual" in name or "mtp" in name or not isinstance(mod, nn.Linear) or not TARGET.search(name): continue
        parent = m.get_submodule(name.rsplit(".", 1)[0]); setattr(parent, name.rsplit(".", 1)[1], LoRA(mod))
        names.append(name)
    return names


def lm_loss(lm_head, h, labels):
    """sum of CE over positions with label != -100, computed in chunks so full-vocab logits are never all stored."""
    tot = h.new_zeros((), dtype=torch.float32)
    for s in range(0, h.shape[0], CHUNK):
        y = labels[s:s + CHUNK]
        if (y != -100).any():
            tot = tot + checkpoint(lambda hh, yy: nn.functional.cross_entropy(lm_head(hh).float(), yy,
                                                                             ignore_index=-100, reduction="sum"),
                                   h[s:s + CHUNK], y, use_reentrant=False)
    return tot


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--data"); ap.add_argument("--work"); ap.add_argument("--out")
    ap.add_argument("--max_steps", type=int, default=0, help="smoke test only"); a = ap.parse_args()
    from transformers import AutoTokenizer, AutoModelForCausalLM
    random.seed(SEED); torch.manual_seed(SEED); os.makedirs(a.work, exist_ok=True)
    tok = AutoTokenizer.from_pretrained(BASE); eos = tok.convert_tokens_to_ids("<|im_end|>")
    rows = [json.loads(l) for l in open(a.data)]; data = []
    for r in rows:
        p = tok.apply_chat_template([{"role": "user", "content": r["problem"] + "\n" + INSTR}], tokenize=False,
                                    add_generation_prompt=True, enable_thinking=True)
        pi = tok(p, add_special_tokens=False).input_ids; ai = tok(r["text"], add_special_tokens=False).input_ids + [eos]
        data.append((pi, ai))
    order = []
    for e in range(EPOCHS):
        o = list(range(len(data))); random.Random(SEED + e).shuffle(o); order += o
    steps = math.ceil(len(order) / BATCH) if not a.max_steps else a.max_steps
    m = AutoModelForCausalLM.from_pretrained(BASE, dtype=torch.float16).to("cuda")
    for p in m.parameters(): p.requires_grad_(False)
    names = wrap(m); m.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False}); m.train()
    body = m.model.language_model if hasattr(m.model, "language_model") else m.model
    params = [p for p in m.parameters() if p.requires_grad]
    print(f"examples {len(data)} steps {steps} lora modules {len(names)} trainable {sum(p.numel() for p in params)}",
          flush=True)
    opt = torch.optim.AdamW(params, lr=LR, weight_decay=0.0, betas=(0.9, 0.999))
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: (s + 1) / max(1, int(WARM * steps)) if s < int(WARM * steps)
                                              else 0.5 * (1 + math.cos(math.pi * (s - int(WARM * steps)) /
                                                                     max(1, steps - int(WARM * steps)))))
    scaler = torch.amp.GradScaler("cuda", init_scale=2.0 ** 12); step = 0; ck = os.path.join(a.work, "ckpt.pt")
    if os.path.exists(ck):
        c = torch.load(ck, map_location="cuda"); step = c["step"]
        for p, v in zip(params, c["params"]): p.data.copy_(v)
        opt.load_state_dict(c["opt"]); sched.load_state_dict(c["sched"]); scaler.load_state_dict(c["scaler"])
        print("resumed at step", step, flush=True)
    log = open(os.path.join(a.work, "train_log.jsonl"), "a"); t0 = time.time()
    while step < steps:
        batch = order[step * BATCH:(step + 1) * BATCH]; ntok = sum(len(data[i][1]) for i in batch); lsum = 0.0
        for i in batch:
            pi, ai = data[i]; x = torch.tensor([pi + ai], device="cuda")
            y = torch.tensor([-100] * (len(pi) - 1) + ai + [-100], device="cuda")[None]  # predict token t+1 at t
            with torch.autocast("cuda", dtype=torch.float16):
                h = body(input_ids=x).last_hidden_state[0]
                loss = lm_loss(m.lm_head, h, y[0, :]) / ntok
            scaler.scale(loss).backward(); lsum += float(loss) * ntok
        scaler.unscale_(opt); gn = float(torch.nn.utils.clip_grad_norm_(params, CLIP))
        scaler.step(opt); scaler.update(); opt.zero_grad(set_to_none=True); sched.step(); step += 1
        rec = {"step": step, "loss": lsum / ntok, "tokens": ntok, "grad_norm": gn, "lr": sched.get_last_lr()[0],
               "scale": scaler.get_scale(), "elapsed": time.time() - t0, "mem_gb": torch.cuda.max_memory_allocated() / 1e9}
        log.write(json.dumps(rec) + "\n"); log.flush(); print(json.dumps(rec), flush=True)
        if step % 10 == 0 or step == steps:
            torch.save({"step": step, "params": [p.detach() for p in params], "opt": opt.state_dict(),
                        "sched": sched.state_dict(), "scaler": scaler.state_dict()}, ck + ".tmp"); os.replace(ck + ".tmp", ck)
    if a.max_steps and not a.out: return
    # merge: W' = W + SCALE * B A, in float64, stored in the base dtype (bf16) like the other edited models
    from safetensors import safe_open
    from safetensors.torch import save_file
    os.makedirs(a.out, exist_ok=True)
    for f in os.listdir(BASE):
        if not f.endswith(".safetensors") and not os.path.exists(os.path.join(a.out, f)):
            os.symlink(os.path.abspath(os.path.join(BASE, f)), os.path.join(a.out, f))
    T = {}
    with safe_open(os.path.join(BASE, ST), "pt") as f:
        meta = f.metadata() or {}
        for k in f.keys(): T[k] = f.get_tensor(k)
    merged = 0
    for name in names:
        mod = m.get_submodule(name); l, sub = TARGET.search(name).groups()
        k = f"model.language_model.layers.{l}.{sub}.weight"; w = T[k].double()
        T[k] = (w + SCALE * (mod.B.detach().double().cpu() @ mod.A.detach().double().cpu())).to(T[k].dtype); merged += 1
    save_file(T, os.path.join(a.out, ST), metadata={**meta, "format": "pt", "c_train": json.dumps({"data": a.data})})
    json.dump({"data": a.data, "examples": len(data), "steps": steps, "merged": merged}, open(os.path.join(a.out,
              "c_train.json"), "w"))
    print("merged", merged, "->", a.out)


if __name__ == "__main__":
    main()
