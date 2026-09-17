"""Generate compact IEEE tables (akatable) + cetz-plot figures from evidence.
Single source of truth — main.typ only #includes these outputs."""
import csv
import math
import os

EV = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "evidence")
P = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
               "paper")
os.makedirs(f"{P}/tables", exist_ok=True)
os.makedirs(f"{P}/figs", exist_ok=True)


def aka(label, caption, header, rows, ncols, extra=""):
    cells = ",\n    ".join(", ".join(f"[{c}]" for c in r) for r in rows)
    head = ", ".join(f"[{c}]" for c in header)
    return ('#import "@preview/akatable:0.1.0": academic-table\n'
            f'#academic-table([{caption}],\n  (\n    {cells}\n  ),\n'
            f'  format: "ieee", header: ({head},),\n'
            f'  label: <{label}>, columns: {ncols}, align: center, inset: 4pt{extra})\n')


def f3(x):
    return f"{float(x):.3f}"


def f4(x):
    return f"{float(x):.4f}"


# ---- RQ1 energy (compact) ----
rows = []
for r in csv.DictReader(open(f"{EV}/rq1/summary.csv")):
    rows.append([r["batch"], r["in_len"], r["n"], f4(r["median"]),
                 f'[{f4(r["ci95_lo"])}, {f4(r["ci95_hi"])}]'])
open(f"{P}/tables/rq1_energy.typ", "w").write(
    aka("tab:rq1", "Energy per token, Qwen2.5-0.5B fp16 on 2xT4 (N=30/cell).",
        ["B", "Ctx", "N", "Med J/tok", "95% CI"], rows, 5))

# ---- Quant (compact) ----
rows = []
for r in csv.DictReader(open(f"{EV}/rq1/summary_quant.csv")):
    rows.append([r["quant"], r["batch"], r["in_len"], f4(r["median"]),
                 f'[{f4(r["ci95_lo"])}, {f4(r["ci95_hi"])}]'])
open(f"{P}/tables/rq1_quant.typ", "w").write(
    aka("tab:quant", "Quantization effect on J/token (bitsandbytes).",
        ["Q", "B", "Ctx", "Med", "95% CI"], rows, 5))

# ---- RQ2 headline (compact) ----
ORDER = ["ldp", "round_robin", "least_rtt", "latency_only", "carbon_blind_slo"]
NAME = {"ldp": "LDP (ours)", "round_robin": "Round-robin",
        "least_rtt": "Least-RTT", "latency_only": "Latency-only",
        "carbon_blind_slo": "C-blind SLO"}
dat = {(r["policy"], r["metric"]): r
       for r in csv.DictReader(open(f"{EV}/eval/results.csv"))}
rows = []
for p in ORDER:
    g, v, t = dat[(p, "gco2e")], dat[(p, "viol_rate")], dat[(p, "p99_ttft")]
    w = dat[(p, "gco2e")]["wilcoxon_vs_ldp"]
    # round(p,5)==0.0 implies p<5e-6, so "<0.001" is exact, never "0.0"
    w = "--" if not w else ("\\<0.001" if float(w) == 0.0 else w)
    rows.append([NAME[p], f'{f4(g["mean"])} [{f4(g["ci95_lo"])}, {f4(g["ci95_hi"])}]',
                 f'{float(v["mean"]) * 100:.2f}%', f'{float(t["mean"]):.1f}', w])
open(f"{P}/tables/rq2_headline.typ", "w").write(
    aka("tab:rq2", "Headline results (Azure 40k).",
        ["Policy", "gCO2e/1k", "Viol", "p99 ms", "p"], rows, 5))

# ---- RQ3 (compact) ----
rows = [[r["rtt_scale"], r["carbon_noise"], f4(r["ldp_gco2e"]), f4(r["lat_gco2e"]),
         f'{float(r["saving"]) * 100:.1f}%', f'{float(r["ldp_viol"]) * 100:.2f}%']
        for r in csv.DictReader(open(f"{EV}/eval/sensitivity.csv"))]
open(f"{P}/tables/rq3_sens.typ", "w").write(
    aka("tab:rq3", "Savings vs latency-only under RTT scale and noise (N=10/cell).",
        ["RTT", "Noise", "LDP", "Lat", "Save", "Viol"], rows, 6))

# ---- RQ4: SLO-140 slice (single row: V is decision-invariant, enforced) ----
r140 = [r for r in csv.DictReader(open(f"{EV}/eval/pareto.csv"))
        if r["slo_ttft"] == "140"]
vals = {(r["gco2e"], r["p99_ttft"], r["viol_rate"]) for r in r140}
assert len(vals) == 1, f"V-invariance broken, slice must show all rows: {vals}"
g, p99, v = vals.pop()
rows = [[f'{r140[0]["V"]}--{r140[-1]["V"]}', g, p99,
         f'{float(v) * 100:.2f}%']]
open(f"{P}/tables/rq4_slice.typ", "w").write(
    aka("tab:rq4", "Frontier slice at SLO 140 ms: identical for all V (Fig. 3; N=10/cell).",
        ["V", "gCO2e/1k", "p99 ms", "Viol"], rows, 4))

# ---- Fig: RQ1 log2-spaced energy vs batch (linear axis, log-spaced positions) ----
# NOTE: 95% CIs are an order of magnitude tighter than markers (see Table I);
# errorbars are intentionally omitted — at this y-range (±0.01 on a 0-1.5 axis)
# only the whisker caps render, which reads as horizontal noise.
series = {}
for r in csv.DictReader(open(f"{EV}/rq1/summary.csv")):
    lb = int(math.log2(int(r["batch"])))
    series.setdefault(r["in_len"], []).append((lb, float(r["median"])))
adds = []
for cin, pts in sorted(series.items()):
    data = ", ".join(f"({x}, {y})" for x, y in sorted(pts))
    adds.append(f'plot.add(({data},), mark: "o", label: [C={cin}])')
head = '#import "@preview/cetz:0.5.2"\n'
head += '#import "@preview/cetz-plot:0.1.4": plot\n'
head += "#cetz.canvas({\n  plot.plot(size: (7.2, 4.2),\n"
head += "    x-label: [Batch size], y-label: [J/token],\n"
head += "    x-min: -0.5, x-max: 4.5,\n"
head += "    x-ticks: ((0, [1]), (2, [4]), (4, [16])), x-tick-step: none,\n"
head += "    legend: auto, {\n"
tail = "\n  })\n})\n"
open(f"{P}/figs/rq1_plot.typ", "w").write(head + "    " + "\n    ".join(adds) + tail)


# ---- Fig: RQ4 Pareto carbon vs p99 ----
# NOTE: V in [0.1, 5] is decision-invariant under the hard filter (all five V
# rows per SLO are identical in pareto.csv), so each SLO collapses to one
# frontier point. A single connected series shows carbon falling as the SLO
# relaxes; points are SLO 100/120/140/180 left to right.
frontier = {}
for r in csv.DictReader(open(f"{EV}/eval/pareto.csv")):
    frontier[r["slo_ttft"]] = (float(r["p99_ttft"]), float(r["gco2e"]))
pts = sorted(frontier.values())
data = ", ".join(f"({x}, {y})" for x, y in pts)
adds = [f'plot.add(({data},), mark: "o", label: [frontier])']
open(f"{P}/figs/pareto_plot.typ", "w").write(
    '#import "@preview/cetz:0.5.2"\n'
    '#import "@preview/cetz-plot:0.1.4": plot\n'
    "#cetz.canvas({\n  plot.plot(size: (7.2, 4.2),\n"
    "    x-label: [p99 TTFT (ms)], y-label: [gCO2e/1k tok],\n"
    "    y-min: 0.0071, y-max: 0.0081,\n"
    "    y-ticks: ((0.0072, [0.0072]), (0.0074, [0.0074]), (0.0076, [0.0076]), (0.0078, [0.0078])), y-tick-step: none,\n"
    "    legend: auto, {\n    " + "\n    ".join(adds) +
    "\n  })\n})\n")

print("tables+figs regenerated")
