"""RQ4 Pareto (Actions CPU): V sweep x SLO sweep -> (carbon, p99 TTFT, viol).
V{0.1,0.5,1,2,5} x SLO_TTFT{120,140,180}, N=10 seeds on Azure sample.
Outputs pareto.csv — the carbon/latency frontier. Topology EMULATED (G2).
"""
import csv
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sim as S
from router.ldp import LDPRouter, RegionState


def main():
    jt = S.load_jtable()
    wl = S.load_workload()
    with open(os.path.join(S.DATA, "carbon_snapshot.json")) as f:
        carbon = statistics.median(json.load(f).values())
    out = []
    for V in (0.1, 0.5, 1.0, 2.0, 5.0):
        for slo in (100, 120, 140, 180):
            gs, ps, vs = [], [], []
            for s in range(10):
                regs = [RegionState(n, carbon * m, rtt, jt[(4, 128)])
                        for (n, _c, rtt), m in zip(S.TOPO, (0.4, 1.0, 1.8))]
                r = S.run_policy(lambda: LDPRouter(regs, slo, 40, V=V), wl,
                                 3000 + s, slo_ttft=slo, slo_itl=40)
                gs.append(r["gco2e"])
                ps.append(r["p99_ttft"])
                vs.append(r["viol_rate"])
            out.append({"V": V, "slo_ttft": slo,
                        "gco2e": round(statistics.mean(gs), 4),
                        "p99_ttft": round(statistics.mean(ps), 1),
                        "viol_rate": round(statistics.mean(vs), 4)})
            print(out[-1], flush=True)
    with open("pareto.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    print("wrote pareto.csv (RQ4)")


if __name__ == "__main__":
    main()
