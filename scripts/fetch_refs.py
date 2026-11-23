"""Resolve every corpus DOI via doi.org CSL-JSON (DataCite/Crossref) -> lit/refs.json {key: csl}."""
import json, subprocess, time, os, glob
out = json.load(open("lit/refs.json")) if os.path.exists("lit/refs.json") else {}
items = [json.loads(l) for l in open("lit/manifest.jsonl")]
extra = [{"key": "zenodo_24398164", "doi": "10.5281/zenodo.24398164"}]
for m in items + extra:
    k, doi = m["key"], m.get("doi")
    if not doi or k in out or not os.path.exists(f"lit/extract/{k}.json"): continue
    r = subprocess.run(["curl", "-sL", "-H", "Accept: application/vnd.citationstyles.csl+json", f"https://doi.org/{doi}"],
                       capture_output=True, text=True, timeout=60).stdout
    try: out[k] = json.loads(r); print("ok", k)
    except Exception: print("FAIL", k, r[:80])
    time.sleep(0.4)
json.dump(out, open("lit/refs.json", "w"), indent=0)
print(len(out), "resolved of", len(glob.glob("lit/extract/*.json")))
