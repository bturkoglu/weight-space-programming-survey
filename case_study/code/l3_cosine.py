"""L3 (PROTOCOL): |cosine| between the output direction of each published edit (top left singular vector of the weight
change of each edited tensor) and the B2 difference-of-means direction of the same layer (results/b2/dirs.pt, from our
own practice generations of the unedited model). Baseline: |cos| of random unit vectors in 1,024 dims ~ 0.025.
Usage: python code/l3_cosine.py  -> results/l3_cosine.json"""
import json, os, re, sys, torch
from safetensors import safe_open
sys.path.insert(0, "code"); from edits import load_edit, BASE
D = torch.load("results/b2/dirs.pt")["diff"].double(); out = {}
for run in ("p10c", "p25c", "p50c"):
    E = load_edit(f"external/lm_understand-logs/exp8_math/runs/{run}/edit"); rows = []
    with safe_open(BASE, "pt") as f:
        for k, (w, ok) in E.items():
            assert ok, k
            dW = w.double() - f.get_tensor(k).double()
            if dW.shape[0] != D.shape[1]: continue  # only matrices that write into the residual stream
            l = int(re.search(r"layers\.(\d+)\.", k).group(1))
            if l >= D.shape[0]: continue
            U, S, _ = torch.linalg.svd(dW, full_matrices=False); u = U[:, 0]
            rows.append({"tensor": k, "layer": l, "rank1_share": round(float(S[0] ** 2 / (S ** 2).sum()), 3),
                         "abs_cos_b2": round(abs(float(u @ D[l] / D[l].norm())), 3)})
    out[run] = rows; print(run, [(r["layer"], r["tensor"].split(".")[-2], r["abs_cos_b2"]) for r in rows])
json.dump(out, open("results/l3_cosine.json", "w"), indent=1)
