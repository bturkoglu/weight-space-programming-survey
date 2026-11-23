"""Own re-implementation of the MIT edit format (data only; does not import their code).
load_edit(run_dir, base_state) -> {tensor_name: edited torch.bfloat16 tensor}, verified by sha256 of bf16 bytes.
Usage: python code/edits.py <run edit dir>   (verifies hashes against the base model)"""
import hashlib, json, os, sys
import numpy as np, torch
from safetensors import safe_open

BASE = os.path.join(os.path.dirname(__file__), "..", "models", "Qwen3.5-0.8B", "model.safetensors-00001-of-00001.safetensors")

def bf16_bits(t):  # torch bf16 -> uint16 numpy
    return t.contiguous().view(torch.int16).numpy().view(np.uint16)

def from_bits(b):
    return torch.from_numpy(np.ascontiguousarray(b).view(np.int16)).view(torch.bfloat16)

def sha(b): return hashlib.sha256(np.ascontiguousarray(b).tobytes()).hexdigest()

def load_edit(edit_dir, base_path=BASE):
    man = json.load(open(os.path.join(edit_dir, "manifest.json")))
    z = np.load(os.path.join(edit_dir, "edit.npz"), allow_pickle=False)
    out = {}
    with safe_open(base_path, "pt") as f:
        for i, t in enumerate(man["tensors"]):
            base = f.get_tensor(t["name"]); b = bf16_bits(base)
            assert sha(b) == t["base_sha256"], t["name"]
            if t["form"] == "lowrank":
                w = base.float().double()
                a, c = torch.from_numpy(z[f"t{i}_a"]).double(), torch.from_numpy(z[f"t{i}_b"]).double()
                w = w + a @ c
                e = bf16_bits(w.float().to(torch.bfloat16)).reshape(-1).copy()
            else:
                e = b.reshape(-1).copy()
            e[z[f"t{i}_idx"]] = z[f"t{i}_val"].astype(np.uint16) if z[f"t{i}_val"].dtype != np.uint16 else z[f"t{i}_val"]
            e = e.reshape(b.shape)
            ok = sha(e) == t["edited_sha256"]
            out[t["name"]] = (from_bits(e), ok)
    return out

if __name__ == "__main__":
    r = load_edit(sys.argv[1])
    for k, (v, ok) in r.items(): print(k, tuple(v.shape), "hash OK" if ok else "HASH MISMATCH")
