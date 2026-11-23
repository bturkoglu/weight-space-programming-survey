"""Build survey tables and figures from ../wsp-exposed/lit/extract (verified extracts) and lit/refs.json."""
import json, glob, os, collections, datetime
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
L = os.environ.get("WSP_LIT", "lit"); O = os.environ.get("WSP_OUT", ".")
E = {os.path.basename(f)[:-5]: json.load(open(f)) for f in glob.glob(f"{L}/extract/*.json")}
R = json.load(open(f"{L}/refs.json"))
CL = json.load(open(f"{L}/classification.json"))
W = {k: e for k, e in E.items() if CL[k]["group"] == "A"}
WB = {k: e for k, e in E.items() if CL[k]["group"] == "B"}
def yes(e, f): return str(e["evidence_quality"].get(f, "")).lower().startswith("yes")
def first_author(k):
    a = (R.get(k, {}).get("author") or [{}])[0]
    return a.get("family") or a.get("literal") or (E[k]["authors"][0].split()[-1] if E[k]["authors"] else "?")
def date(k): return E[k]["date"][:10]
# Table III: one row per WSP study
ROLE = {"read": "R", "write_from_scratch": "W", "repair_or_edit": "E", "feedback_loop": "F", "self_rewrite": "S"}
rows = []
for k, e in sorted(W.items(), key=lambda x: (date(x[0]), x[0])):
    tn = "; ".join(f'{t["name"]} ({t["params"]})' for t in e["target_networks"][:2])
    ed = ", ".join(m.split("(")[0].strip() for m in e["editor_models"][:2])
    ctl = "".join(c for c, f in [("C", "random_or_null_control"), ("B", "non_llm_baseline"), ("T", "finetune_comparison"),
                                  ("I", "inference_only_fix_tested"), ("P", "preregistered"), ("O", "code_or_data_released")] if yes(e, f))
    rows.append({"key": k, "first_author": first_author(k), "date": date(k), "type": e["doc_type"],
                 "roles": "".join(ROLE.get(r, "") for r in e["wsp_role"]), "editor": ed, "target": tn,
                 "domain": e["domain"][:60], "checks": ctl or "-"})
json.dump(rows, open(f"{O}/tables/table3_studies.json", "w"), indent=1)
with open(f"{O}/tables/table3_studies.md", "w") as f:
    f.write("| Study | Date | Type | Role | Editor LLM | Target network | Domain | Checks |\n|---|---|---|---|---|---|---|---|\n")
    for r in rows: f.write(f'| {r["first_author"]} [{r["key"]}] | {r["date"]} | {r["type"]} | {r["roles"]} | {r["editor"]} | {r["target"]} | {r["domain"]} | {r["checks"]} |\n')
# evidence shares
F = [("random_or_null_control", "Random or null control"), ("non_llm_baseline", "Any non-LLM comparator"),
     ("finetune_comparison", "Comparison with fine-tuning"), ("inference_only_fix_tested", "Inference-only fix tested"),
     ("full_test_set", "Full test set"), ("preregistered", "Pre-registered"), ("code_or_data_released", "Code or data released"),
     ("peer_reviewed", "Peer reviewed")]
ev = {lab: sum(yes(e, f) for e in W.values()) for f, lab in F}
json.dump({"n": len(W), "n_groupB": len(WB), "counts": ev, "types": collections.Counter(e["doc_type"] for e in W.values()),
           "roles": collections.Counter(r for e in W.values() for r in e["wsp_role"])},
          open(f"{O}/tables/evidence_counts.json", "w"), indent=1)
plt.rcParams.update({"font.size": 8, "font.family": "DejaVu Sans", "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "axes.labelcolor": "#0b0b0b", "xtick.color": "#52514e", "ytick.color": "#52514e"})
# Fig 3: evidence audit
fig, ax = plt.subplots(figsize=(3.4, 2.2)); labs = [l for _, l in F][::-1]; vals = [100 * ev[l] / len(W) for l in labs]
ax.barh(labs, vals, color="#2a78d6", height=0.6)
for i, v in enumerate(vals): ax.text(v + 1.5, i, f"{v:.0f}% ({round(v * len(W) / 100)})", va="center", color="#0b0b0b", fontsize=7)
ax.set_xlim(0, 100); ax.set_xlabel(f"Share of the {len(W)} studies with an LLM editor (%)"); ax.grid(axis="x", color="#e5e4e0", lw=0.5); ax.set_axisbelow(True)
fig.tight_layout(); fig.savefig(f"{O}/figs/fig3_evidence.pdf"); fig.savefig(f"{O}/figs/fig3_evidence.png", dpi=200)
# Fig 2: studies per day since the MIT post
d0 = datetime.date(2026, 11, 2); cnt = collections.Counter(date(k) for k in list(W) + list(WB))
days = [d0 + datetime.timedelta(i) for i in range(0, 20)]; v = [cnt.get(d.isoformat(), 0) for d in days]
fig, ax = plt.subplots(figsize=(3.4, 1.8)); ax.bar([d.day for d in days], v, color="#2a78d6", width=0.7)
ax.axvline(2, color="#52514e", lw=0.8, ls=":"); ax.text(2.3, max(v) * 0.95, "MIT post", fontsize=7, color="#52514e")
ax.set_xlabel("November 2026 (day)"); ax.set_ylabel("New WSP studies"); ax.grid(axis="y", color="#e5e4e0", lw=0.5); ax.set_axisbelow(True)
fig.tight_layout(); fig.savefig(f"{O}/figs/fig2_timeline.pdf"); fig.savefig(f"{O}/figs/fig2_timeline.png", dpi=200)
print("WSP studies", len(W), ev); print("per day", dict(zip([d.day for d in days], v)))
