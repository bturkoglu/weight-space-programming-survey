"""v0.3 tables/figures from second-pass coding (lit/code2) over primary group-A studies."""
import json, glob, os, collections
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
L = os.environ.get("WSP_LIT", "lit")
CL = json.load(open(f"{L}/classification.json")); R = json.load(open(f"{L}/refs.json"))
E = {os.path.basename(f)[:-5]: json.load(open(f)) for f in glob.glob(f"{L}/extract/*.json")}
C = {os.path.basename(f)[:-5]: json.load(open(f)) for f in glob.glob(f"{L}/code2/*.json")}
A = sorted(k for k in CL if CL[k]["group"] == "A"); AP = [k for k in A if not C[k]["peripheral"]]; n = len(AP)
y = lambda v: str(v).lower().startswith("yes")
INK, MUTED, BLUE = "#0b0b0b", "#52514e", "#2a78d6"
plt.rcParams.update({"font.size": 7, "font.family": "DejaVu Sans", "axes.spines.top": False, "axes.spines.right": False})
ev = lambda f: sum(y(C[k]["wsp_evidence"][f]) for k in AP)
items = [("Held-out evaluation", ev("held_out_eval")), ("Any non-LLM comparator", ev("non_llm_baseline")),
         ("More than one session or seed", ev("multiple_runs")), ("Full test set", ev("full_test_set")),
         ("Cost (money or time) reported", sum(C[k]["cost_reported"] != "no" for k in AP)),
         ("Random or null control", ev("random_or_null_control")), ("Fine-tuning comparison", ev("finetune_comparison")),
         ("Code or data released (link)", ev("code_or_data_released")), ("Inference-only fix tested", ev("inference_only_fix_tested")),
         ("Pre-specified (internal or partial)", sum(C[k]["prereg"] in ("internal", "partial") for k in AP)),
         ("Pre-registered with a third party", sum(C[k]["prereg"] == "public" for k in AP)), ("Peer reviewed", 0)]
fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.0, 2.4), gridspec_kw={"width_ratios": [1.5, 1]})
labs = [i[0] for i in items][::-1]; vals = [100 * i[1] / n for i in items][::-1]; cnt = [i[1] for i in items][::-1]
a1.barh(labs, vals, color=BLUE, height=0.62)
for i, (v, c) in enumerate(zip(vals, cnt)): a1.text(v + 1.5, i, f"{c}/{n} ({v:.0f}%)", va="center", fontsize=6.3, color=INK)
a1.set_xlim(0, 115); a1.set_xticks([0, 25, 50, 75, 100]); a1.set_xlabel("Share of primary studies with an LLM editor (%)")
a1.set_title("(a) Checks reported", fontsize=7.5, loc="left")
bins = ["<1k", "1k-1M", "1M-100M", "100M-1B", ">=1B"]
def b(s): return "<1k" if s < 1e3 else "1k-1M" if s < 1e6 else "1M-100M" if s < 1e8 else "100M-1B" if s < 1e9 else ">=1B"
sz = collections.Counter(b(C[k]["target_params_max"]) for k in AP if isinstance(C[k]["target_params_max"], (int, float)))
nk = sum(sz.values()); a2.bar(range(5), [sz[x] for x in bins], color=BLUE, width=0.62); a2.set_xticks(range(5)); a2.set_xticklabels(["<1k", "1k\n-1M", "1M\n-100M", "100M\n-1B", "1B+"], fontsize=6.3)
for i, x in enumerate(bins): a2.text(i, sz[x] + 0.3, str(sz[x]), ha="center", fontsize=6.5, color=INK)
a2.set_xlabel("Largest target network (parameters)"); a2.set_ylabel("Studies"); a2.set_title(f"(b) Target size (size stated: {nk} of {n})", fontsize=7.5, loc="left")
for ax in (a1, a2): ax.grid(axis="x" if ax is a1 else "y", color="#e5e4e0", lw=0.5); ax.set_axisbelow(True)
fig.tight_layout(); fig.savefig("figs/fig3_evidence.pdf"); fig.savefig("figs/fig3_evidence.png", dpi=220)
# Fig 1: taxonomy schematic with counts
cc = lambda field: collections.Counter(v for k in AP for v in (C[k][field] if isinstance(C[k][field], list) else [C[k][field]]))
op, pr, me, sc = cc("operation"), cc("protocol"), cc("mechanism"), cc("scope")
fig, ax = plt.subplots(figsize=(7.0, 2.3)); ax.axis("off"); ax.set_xlim(0, 20); ax.set_ylim(0, 6.2)
cols = [("Operation", [f"Read  ({op['read']})", f"Write from scratch  ({op['write']})", f"Edit or repair  ({op['edit']})"]),
        ("Protocol", [f"Open loop  ({pr['open_loop']})", f"Closed loop  ({pr['closed_loop']})", f"Both  ({pr['both']})"]),
        ("Mechanism", [f"Direct values  ({me['direct_values']})", f"Code or tensor tools  ({me['code_or_tensor_tool']})", f"Solver-delegated  ({me['solver_delegated']})"]),
        ("Scope", [f"External network  ({sc['external']})", f"Own weights  ({sc['self']})", ""])]
for i, (h, rows) in enumerate(cols):
    x = 0.2 + i * 5; ax.text(x + 2.3, 5.75, h, ha="center", fontsize=8, weight="bold", color=INK)
    for j, r in enumerate(rows):
        if not r: continue
        ax.add_patch(FancyBboxPatch((x, 4.1 - j * 1.55), 4.6, 1.15, boxstyle="round,pad=0.03,rounding_size=0.15", fc="white", ec=BLUE, lw=0.9))
        ax.text(x + 2.3, 4.67 - j * 1.55, r, ha="center", va="center", fontsize=7, color=INK)
ax.text(0.2, 0.05, f"Counts over {n} primary studies with an LLM editor; a study can fall in several cells of an axis.", fontsize=6.3, color=MUTED)
fig.tight_layout(); fig.savefig("figs/fig1_taxonomy.pdf"); fig.savefig("figs/fig1_taxonomy.png", dpi=220)
# Failure modes table
FM = {"simple_baseline_matches": ("A simple baseline matches the LLM", "random, mechanical and inference-only baselines"),
      "editor_refusal_or_unfinished": ("Editor refuses or does not finish", "count unfinished runs as failures"),
      "run_to_run_variance": ("Large run-to-run variance", "several sessions and seeds"),
      "proxy_overfitting": ("Gains on the proxy do not transfer", "held-out and full test sets"),
      "layout_or_prior_fallback": ("Reading follows layout or priors", "permuted labels, function-preserving rewrites"),
      "known_rule_rediscovered": ("A known rule is rediscovered", "compare with the known rule"),
      "numerical_artifact": ("Numerical artefacts (float formats)", "report number format, rounded controls"),
      "fragile_to_perturbation_or_retraining": ("Written weights break under retraining or perturbation", "perturbation and retraining tests")}
fmc = collections.defaultdict(list)
for k in AP:
    for m in C[k]["failure_modes"]: fmc[m].append(k)
with open("tables/table_failure_modes.md", "w") as f:
    f.write("| Failure mode | Studies (n) | Examples | Control that catches it |\n|---|---|---|---|\n")
    for m, (lab, ctl) in sorted(FM.items(), key=lambda x: -len(fmc[x[0]])):
        f.write(f"| {lab} | {len(fmc[m])} | {', '.join('['+k+']' for k in fmc[m][:4])} | {ctl} |\n")
# Appendix index
def fa(k):
    a = (R.get(k, {}).get("author") or [{}])[0]; return a.get("family") or a.get("literal") or "?"
with open("tables/appendix_index.md", "w") as f:
    f.write("| Study | Date | Group | Operation | Protocol | Mechanism | Editor tier | Largest target | Domain |\n|---|---|---|---|---|---|---|---|---|\n")
    for k in sorted([k for k in CL if CL[k]["group"] in "AB"], key=lambda k: (E[k]["date"][:10], k)):
        c = C[k]; s = c["target_params_max"]
        st = "?" if not isinstance(s, (int, float)) else (f"{s/1e9:.1f}B" if s >= 1e9 else f"{s/1e6:.1f}M" if s >= 1e6 else f"{s/1e3:.1f}k" if s >= 1e3 else str(int(s)))
        g = CL[k]["group"] + ("*" if c["peripheral"] else "")
        f.write(f"| {fa(k)} [{k}] | {E[k]['date'][:10]} | {g} | {', '.join(c['operation'])} | {c['protocol']} | {', '.join(c['mechanism'])} | {', '.join(c['editor_tier'])} | {st} | {E[k]['domain'][:45]} |\n")
stats = {"n_primary": n, "peripheral": [k for k in A if C[k]["peripheral"]], "items": items, "operation": op, "protocol": pr,
         "mechanism": me, "scope": sc, "tier": cc("editor_tier"), "ow_failed": cc("open_weight_editor_failed"),
         "llm_authoring": cc("llm_in_authoring_or_grading"), "prereg": cc("prereg"), "size_bins": sz, "size_known": nk,
         "failure_modes": {m: len(v) for m, v in fmc.items()}}
json.dump(stats, open("tables/v03_stats.json", "w"), indent=1, default=dict); print(json.dumps(stats, default=dict)[:1500])
