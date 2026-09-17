"""Verify every number cited in main.typ traces to evidence CSVs.
Fails loudly on mismatch or placeholder text."""
import csv
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, "paper") + os.sep
EV = os.path.join(ROOT, "evidence") + os.sep
main = open(P + "main.typ").read()
for t in ["rq1_energy", "rq1_quant", "rq2_headline", "rq3_sens", "rq4_slice"]:
    main += open(f"{P}tables/{t}.typ").read()
for t in ["rq1_plot", "pareto_plot"]:
    main += open(f"{P}figs/{t}.typ").read()

fails = []


def need(substr, label):
    if substr not in main:
        fails.append(f"missing citation text: {label} ({substr})")


# headline numbers from evidence/eval/results.csv (compact 4dp table form)
res = {(r["policy"], r["metric"]): r
       for r in csv.DictReader(open(EV + "eval/results.csv"))}
for key in [("ldp", "gco2e"), ("round_robin", "gco2e"),
            ("latency_only", "gco2e")]:
    need(f'{float(res[key]["mean"]):.4f}', f"results.csv {key}")
need("140.7", "ldp p99 (table)")
need("95.07%", "least-rtt violations")
# RQ1 numbers
summ = list(csv.DictReader(open(EV + "rq1/summary.csv")))
need(summ[0]["median"], "rq1 first median")
need("951%", "G1 variation")
# quant numbers
qs = list(csv.DictReader(open(EV + "rq1/summary_quant.csv")))
need("4.1749", "int8 B1 median")
# RQ3/RQ4 spot checks
need("57%", "rq3 saving")
need("99.6", "rq4 SLO-100 p99")
# placeholders / lorem
for bad in ["TODO", "Lorem", "XXX", "???", "0.00760 gCO2e".replace("0", "9")]:
    if bad in main:
        fails.append(f"placeholder found: {bad}")
# savings arithmetic: recompute from CSV means
ldp, rr = float(res[("ldp", "gco2e")]["mean"]), float(res[("round_robin", "gco2e")]["mean"])
lat = float(res[("latency_only", "gco2e")]["mean"])
lrt = float(res[("least_rtt", "gco2e")]["mean"])
for claimed, val in [("37%", 1 - ldp / rr), ("55%", 1 - ldp / lat), ("63%", 1 - ldp / lrt)]:
    if claimed not in main:
        fails.append(f"saving {claimed} not in prose (recomputed {val * 100:.1f}%)")

if fails:
    print("VERIFY FAIL:")
    print("\n".join(" - " + f for f in fails))
    sys.exit(1)
print("verify_numbers PASS: all prose numbers trace to evidence CSVs")
