"""RQ3 sensitivity (Actions CPU): RTT scale x carbon forecast-error grid.
Grid: rtt_scale{0.5,1,2} x carbon_noise{0,0.10,0.25 uniform}.
Per cell: LDP vs latency-only on Azure sample, N=10 seeds (screening) —
reports savings retained + violation rate. Outputs sensitivity.csv.
"""
import csv
import json
import os
import random
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sim as S
from router.ldp import LDPRouter, RegionState


def noisy_regions(carbon, jt, rtt_scale, noise, rng):
    regs = []
    for (name, _ci, rtt), mult in zip(S.TOPO, (0.4, 1.0, 1.8)):
        noisy = carbon * mult * (1 + rng.uniform(-noise, noise))
        regs.append(RegionState(name, noisy, rtt * rtt_scale, jt[(4, 128)]))
    return regs


def main():
    jt = S.load_jtable()
    wl = S.load_workload()
    with open(os.path.join(S.DATA, "carbon_snapshot.json")) as f:
        carbon = statistics.median(json.load(f).values())
    out = []
    for rs in (0.5, 1.0, 2.0):
        for nz in (0.0, 0.10, 0.25):
            ldp_m, lat_m, ldp_v = [], [], []
            for s in range(10):
                rng = random.Random(5000 + s)
                mk_ldp = lambda: LDPRouter(  # noqa: E731
                    noisy_regions(carbon, jt, rs, nz, rng), 140, 40, V=1.0)
                mk_lat = lambda: S.LatencyOnly(  # noqa: E731
                    noisy_regions(carbon, jt, rs, nz, rng))
                rl = S.run_policy(mk_ldp, wl, 2000 + s)
                ra = S.run_policy(mk_lat, wl, 2000 + s)
                ldp_m.append(rl["gco2e"])
                lat_m.append(ra["gco2e"])
                ldp_v.append(rl["viol_rate"])
            out.append({"rtt_scale": rs, "carbon_noise": nz,
                        "ldp_gco2e": round(statistics.mean(ldp_m), 4),
                        "lat_gco2e": round(statistics.mean(lat_m), 4),
                        "saving": round(1 - statistics.mean(ldp_m) / statistics.mean(lat_m), 4),
                        "ldp_viol": round(statistics.mean(ldp_v), 4)})
            print(out[-1], flush=True)
    with open("sensitivity.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    print("wrote sensitivity.csv (RQ3)")


if __name__ == "__main__":
    main()
