"""Download open-access full texts of the WSP corpus (lit/openalex_wsp.json, works since 2026-11-01).
arXiv: https://arxiv.org/pdf/<id> (3 s between requests). Zenodo: record API, PDF files only.
Writes lit/pdfs/<key>.pdf and lit/manifest.jsonl {key, doi, title, date, url, bytes, sha256, status}."""
import hashlib, json, os, subprocess, time
D = json.load(open("lit/openalex_wsp.json"))["results"]; os.makedirs("lit/pdfs", exist_ok=True)
done = {json.loads(l)["key"] for l in open("lit/manifest.jsonl")} if os.path.exists("lit/manifest.jsonl") else set()
def get(url, out):
    p = subprocess.run(["curl", "-sL", "-A", "Mozilla/5.0 (research literature review)", "-o", out, "-w", "%{http_code}", url],
                       capture_output=True, text=True, timeout=300); return p.stdout
for w in D:
    if (w["publication_date"] or "") < "2026-11-01": continue
    doi = (w.get("doi") or "").replace("https://doi.org/", ""); rec = {"doi": doi, "title": w["title"], "date": w["publication_date"]}
    if "arxiv" in doi.lower():
        aid = doi.lower().split("arxiv.")[1]; key = "arxiv_" + aid
        if key in done: continue
        url = f"https://arxiv.org/pdf/{aid}"; out = f"lit/pdfs/{key}.pdf"; code = get(url, out); time.sleep(3)
    elif "zenodo" in doi.lower():
        rid = doi.split("zenodo.")[1]; key = "zenodo_" + rid
        if key in done: continue
        meta = subprocess.run(["curl", "-sL", f"https://zenodo.org/api/records/{rid}"], capture_output=True, text=True).stdout
        try: files = [f for f in json.loads(meta).get("files", []) if f["key"].lower().endswith(".pdf")]
        except Exception: files = []
        if not files: rec.update(key=key, status="no_pdf"); open("lit/manifest.jsonl", "a").write(json.dumps(rec) + "\n"); continue
        f0 = sorted(files, key=lambda f: -f["size"])[0]; url = f0["links"]["self"]; out = f"lit/pdfs/{key}.pdf"
        code = get(url, out); time.sleep(1)
    else:
        rec.update(key=doi or w["id"], status="other_source"); open("lit/manifest.jsonl", "a").write(json.dumps(rec) + "\n"); continue
    ok = os.path.exists(out) and open(out, "rb").read(5) == b"%PDF-"
    rec.update(key=key, url=url, http=code, status="ok" if ok else "fail",
               bytes=os.path.getsize(out) if os.path.exists(out) else 0,
               sha256=hashlib.sha256(open(out, "rb").read()).hexdigest() if ok else None)
    if not ok and os.path.exists(out): os.remove(out)
    open("lit/manifest.jsonl", "a").write(json.dumps(rec) + "\n"); print(rec["status"], key, flush=True)
