"""Deterministic check of every quote in lit/extract/*.json against lit/pages/<key>.txt.
Normalisation: lower-case, unify quotes/dashes/ligatures, drop hyphenation at line breaks, collapse whitespace.
Writes lit/quote_check.json and prints per-source pass counts."""
import glob, json, re, unicodedata, os
def norm(s):
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = re.sub(r"[‐-―−]", "-", s)
    s = re.sub(r"-\s*\n\s*", "", s)
    s = re.sub(r"=== (PAGE|FILE) [^=]* ===", " ", s)
    s = re.sub(r"\s+", " ", s).lower().strip()
    return s
def nospace(s): return re.sub(r"[\s\-]", "", s)
out, bad = {}, 0
for f in sorted(glob.glob("lit/extract/*.json")):
    k = os.path.basename(f)[:-5]
    try: d = json.load(open(f))
    except Exception as e: out[k] = {"error": f"json: {e}"}; print(k, "JSON ERROR"); continue
    T = norm(open(f"lit/pages/{k}.txt", errors="ignore").read()); T2 = nospace(T)
    qs = [("headline", d.get("headline_result", {}).get("quote", ""))]
    qs += [("claim", c.get("quote", "")) for c in d.get("key_claims", [])]
    qs += [("limitation", c.get("quote", "")) for c in d.get("limitations_stated", [])]
    res = []
    for kind, q in qs:
        if not q: continue
        n = norm(q); ok = n in T or nospace(n) in T2
        if not ok:  # tolerate ellipsis-joined fragments
            parts = [p.strip() for p in re.split(r"\.\.\.|…", n) if len(p.strip()) > 12]
            ok = bool(parts) and all(p in T or nospace(p) in T2 for p in parts)
        res.append({"kind": kind, "ok": ok, "quote": q[:120]}); bad += not ok
    out[k] = res; print(k, sum(r["ok"] for r in res), "/", len(res))
json.dump(out, open("lit/quote_check.json", "w"), indent=1); print("FAILED QUOTES", bad)
