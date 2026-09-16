"""Generate paper/tables/*.typ from evidence CSVs. Single source of truth:
no hand-transcribed numbers in main.typ. verify_numbers.py re-checks them."""
import csv
import os

EV = "/home/shiva/research/evidence"
OUT = "/home/shiva/research/paper/tables"
os.makedirs(OUT, exist_ok=True)


def cell(v):
    return str(v)


def typ_table(caption, label, columns, rows, align=None):
    n = len(columns)
    al = align or "center"
    head = "table.header(" + ", ".join(f"[{c}]" for c in columns) + ")"
    body = ",\n    ".join(", ".join(f"[{cell(v)}]" for v in r) for r in rows)
    return (f"#figure(\n  table(columns: {n}, align: {al},\n    {head},\n    {body}\n  ),\n"
            f'  caption: [{caption}],\n) <{label}>\n')


# RQ1 fp16 sweep (evidence/rq1/summary.csv)
rows = []
for r in csv.DictReader(open(f"{EV}/rq1/summary.csv")):
    rows.append([r["batch"], r["in_len"], r["n"], r["median"],
                 f'{r["ci95_lo"]}--{r["ci95_hi"]}'])
open(f"{OUT}/rq1_energy.typ", "w").write(typ_table(
    "Measured energy per token, Qwen2.5-0.5B fp16 on 2xT4 (N=30/cell).",
    "tab:rq1",
    ["Batch", "Ctx", "N", "Median J/tok", "95% CI"], rows))

# Quant (evidence/rq1/summary_quant.csv)
rows = []
for r in csv.DictReader(open(f"{EV}/rq1/summary_quant.csv")):
    rows.append([r["quant"], r["batch"], r["in_len"], r["median"],
                 f'{r["ci95_lo"]}--{r["ci95_hi"]}'])
open(f"{OUT}/rq1_quant.typ", "w").write(typ_table(
    "Quantization effect on energy per token, same setup (bitsandbytes).",
    "tab:quant",
    ["Quant", "Batch", "Ctx", "Median J/tok", "95% CI"], rows))

# RQ2 headline (evidence/eval/results.csv)
ORDER = ["ldp", "round_robin", "least_rtt", "latency_only", "carbon_blind_slo"]
NAME = {"ldp": "LDP (ours)", "round_robin": "Round-robin",
        "least_rtt": "Least-RTT", "latency_only": "Latency-only",
        "carbon_blind_slo": "Carbon-blind SLO"}
dat = {(r["policy"], r["metric"]): r
       for r in csv.DictReader(open(f"{EV}/eval/results.csv"))}
rows = []
for p in ORDER:
    g, v, t = dat[(p, "gco2e")], dat[(p, "viol_rate")], dat[(p, "p99_ttft")]
    rows.append([NAME[p], f'{g["mean"]} [{g["ci95_lo"]}, {g["ci95_hi"]}]',
                 f'{float(v["mean"]) * 100:.2f}%', f'{t["mean"]}',
                 dat[(p, "gco2e")]["wilcoxon_vs_ldp"] or "--"])
open(f"{OUT}/rq2_headline.typ", "w").write(typ_table(
    "Headline: gCO2e/1k tokens, violation rate, p99 TTFT (Azure 40k, N=30).",
    "tab:rq2",
    ["Policy", "gCO2e/1k", "Viol", "p99 TTFT ms", "p vs LDP"], rows))

# RQ3 (evidence/eval/sensitivity.csv)
rows = [[r["rtt_scale"], r["carbon_noise"], r["ldp_gco2e"], r["lat_gco2e"],
         f'{float(r["saving"]) * 100:.1f}%', f'{float(r["ldp_viol"]) * 100:.2f}%']
        for r in csv.DictReader(open(f"{EV}/eval/sensitivity.csv"))]
open(f"{OUT}/rq3_sens.typ", "w").write(typ_table(
    "RQ3: savings vs latency-only under RTT scale and carbon-signal noise.",
    "tab:rq3",
    ["RTT x", "Noise", "LDP", "Lat-only", "Saving", "LDP viol"], rows))

# RQ4 (evidence/eval/pareto.csv) — SLO=140 slice + full frontier note
rows = [[r["V"], r["slo_ttft"], r["gco2e"], r["p99_ttft"],
         f'{float(r["viol_rate"]) * 100:.2f}%']
        for r in csv.DictReader(open(f"{EV}/eval/pareto.csv"))]
open(f"{OUT}/rq4_pareto.typ", "w").write(typ_table(
    "RQ4: carbon/latency points over V and SLO (p99 tracks each SLO).",
    "tab:rq4",
    ["V", "SLO", "gCO2e/1k", "p99 ms", "Viol"], rows))

print("tables written:", sorted(os.listdir(OUT)))
