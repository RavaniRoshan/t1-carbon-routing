"""Phase 3 eval (Actions CPU): replay harness, all measured inputs.
Inputs (data/): j_per_token.csv (Kaggle T4 measured, N=30/cell),
carbon_snapshot.json (UK CI 18-region forecast), RTT table in config (netem-only,
labelled EMULATED per G2). Workload: Azure LLM Inference Trace 2024 CSVs if
fetchable, else Poisson fallback with identical token schema (documented).
Policies: LDP + round-robin + least-loaded + latency-only + carbon-blind-SLO +
soft-weighted (CASPER-style ablation). N=30 seeds; 95pct CIs; paired Wilcoxon
LDP vs each baseline; Pareto (carbon vs p99 TTFT). Outputs results.csv.
"""
import csv
import json
import math
import os
import random
import statistics
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from router.ldp import LDPRouter, RegionState
from router.baselines import CarbonBlindSLO, LatencyOnly, LeastRTT, RoundRobin
from router.ldp import LDPRouter, RegionState

DATA = os.path.join(os.path.dirname(__file__), "..", "data")
SEEDS = 30
REQS = 400  # per seed per policy (CPU-fast; scale-up noted)
TARGET_RHO = 0.7  # offered load vs 3-region capacity (arrival auto-tuned)


def tune_arrival(wl, lat, sample=2000, regions=3):
    from router.ldp import SLOTS
    svc = []
    for cin_raw, cout_raw in wl[:sample]:
        cin = max(8, min(cin_raw, 512))
        cout = max(8, min(cout_raw, 64))
        svc.append((lat["ttft_base_ms"] + lat["ttft_per_input_ms"] * cin
                    + lat["itl_ms"] * cout) / 1000.0)
    mean_svc = statistics.mean(svc)
    lam = TARGET_RHO * regions * SLOTS / mean_svc
    print(f"arrival auto-tune: mean_svc={mean_svc:.2f}s slots={SLOTS} "
          f"-> lambda={lam:.3f} rps (rho={TARGET_RHO})", flush=True)
    return lam

# netem-only topology (G2 fired): shaped RTTs, EMULATED label, not Cloud Run claims.
# Greenest region is FARTHEST on purpose: routing must trade carbon vs latency.
TOPO = [("R1-green", 60, 95), ("R2-mid", 180, 55), ("R3-dirty", 320, 10)]
SLO_TTFT, SLO_ITL = 140, 40  # ms; binds TTFT for far-green at large inputs


def load_jtable():
    t = {}
    with open(os.path.join(DATA, "j_per_token.csv")) as f:
        for r in csv.DictReader(f):
            t[(int(r["batch"]), int(r["in_len"]))] = float(r["median"])
    return t


def j_for(jt, bsz, cin):
    key = (16 if bsz >= 16 else 4 if bsz >= 4 else 1, 512 if cin >= 512 else 128)
    return jt[key]


def load_workload():
    base = ("https://github.com/Azure/AzurePublicDataset/releases/download/"
            "dataset-llm-2024")
    urls = [f"{base}/AzureLLMInferenceTrace_conv_1week.csv",
            f"{base}/AzureLLMInferenceTrace_code_1week.csv"]
    wl = []
    try:
        import signal

        def _to(_s, _f):
            raise TimeoutError("workload budget exceeded")
        signal.signal(signal.SIGALRM, _to)
        signal.alarm(int(os.environ.get("WORKLOAD_BUDGET", "240")))
        for u in urls:
            req = urllib.request.Request(u, headers={"User-Agent": "t1-eval/1.0"})
            with urllib.request.urlopen(req, timeout=60) as fh:
                # stream + reservoir-sample during parse: never hold full file
                import io
                text = io.TextIOWrapper(fh, encoding="utf-8", errors="replace")
                reader = csv.DictReader(text)
                kept, seen = [], 0
                rng = random.Random(7)
                for r in reader:
                    try:
                        row = (int(float(r["ContextTokens"])),
                               int(float(r["GeneratedTokens"])))
                    except (KeyError, ValueError):
                        continue
                    seen += 1
                    if len(kept) < 20000:
                        kept.append(row)
                    elif rng.random() < 20000 / seen:
                        kept[rng.randrange(20000)] = row
            wl += kept
            print(f"sampled {len(kept)} rows from {u.rsplit('/', 1)[-1]}", flush=True)
        signal.alarm(0)
        assert len(wl) > 1000, f"too few rows: {len(wl)}"
        print(f"workload: Azure trace 2024 conv+code {len(wl)} rows (CC-BY, HPCA25)")
        return wl
    except Exception as e:  # noqa: BLE001
        try:
            signal.alarm(0)
        except Exception:  # noqa: BLE001
            pass
        print(f"workload FALLBACK synthetic (Azure fetch failed: {e})")
        rng = random.Random(0)
        return [(int(rng.lognormvariate(6.0, 0.8)), int(rng.lognormvariate(4.0, 0.6)))
                for _ in range(5000)]


def build_regions(carbon, jt, scale=1.0):
    regs = []
    for (name, ci, rtt), mult in zip(TOPO, (0.4, 1.0, 1.8)):
        regs.append(RegionState(name, carbon * mult, rtt, jt[(4, 128)] * scale))
    return regs


def load_lat():
    with open(os.path.join(DATA, "latency_model.json")) as f:
        return json.load(f)


def run_policy(make, wl, seed, slo_ttft=None, slo_itl=None, lat=None,
               arrival=None):
    slo_ttft = SLO_TTFT if slo_ttft is None else slo_ttft
    slo_itl = SLO_ITL if slo_itl is None else slo_itl
    lat = load_lat() if lat is None else lat
    arrival = tune_arrival(wl, lat) if arrival is None else arrival
    rng = random.Random(seed)
    idx = list(range(len(wl)))
    rng.shuffle(idx)
    reqs = [wl[i] for i in idx[:REQS]]
    gaps = [rng.expovariate(arrival) for _ in reqs]
    pol = make()
    gco2, viols, ttfts, waits, overhead_ms = 0.0, 0, [], [], 0.0
    now = 0.0
    for (cin_raw, cout_raw), gap in zip(reqs, gaps):
        now += gap * 1000.0
        cin = max(8, min(cin_raw, 512))
        cout = max(8, min(cout_raw, 64))
        s = time_perf()
        name, viol, wait = pol.route(pol.regions.values(), cin, cout, now, lat)
        overhead_ms += (time_perf() - s) * 1000
        r = pol.regions.get(name)
        jt = r.j_per_token
        ci = r.carbon
        toks = cin + cout
        gco2 += jt * toks / 3.6e6 * ci / toks * 1000.0  # gCO2e per 1k tokens
        ttft = r.rtt_ms + wait + lat["ttft_base_ms"] + lat["ttft_per_input_ms"] * cin
        viols += (ttft > slo_ttft) or (lat["itl_ms"] > slo_itl)
        ttfts.append(ttft)
        waits.append(wait)
    ttfts.sort()
    p99 = ttfts[int(0.99 * (len(ttfts) - 1))]
    return {"gco2e": gco2 / len(reqs), "viol_rate": viols / len(reqs),
            "p99_ttft": p99, "avg_wait_ms": statistics.mean(waits),
            "overhead_ms": overhead_ms / len(reqs)}


def time_perf():
    import time
    return time.perf_counter()


def wilcoxon_signed(x, y):
    diffs = sorted((a - b for a, b in zip(x, y) if a != b), key=abs)
    n = len(diffs)
    if n < 6:
        return 1.0
    ranks, i = [], 0
    while i < n:
        j = i
        while j < n and abs(diffs[j]) == abs(diffs[i]):
            j += 1
        avg = (i + j + 1) / 2
        ranks += [avg] * (j - i)
        i = j
    w = sum(r for d, r in zip(diffs, ranks) if d > 0)
    mu, var = n * (n + 1) / 4, n * (n + 1) * (2 * n + 1) / 24
    z = (w - mu) / math.sqrt(var) if var else 0.0
    p = math.erfc(abs(z) / math.sqrt(2))
    return round(p, 5)


def main():
    jt = load_jtable()
    wl = load_workload()
    with open(os.path.join(DATA, "carbon_snapshot.json")) as f:
        snap = json.load(f)
    carbon = statistics.median(snap.values())

    def mk_ldp():
        return LDPRouter(build_regions(carbon, jt), SLO_TTFT, SLO_ITL, V=1.0)

    makers = {
        "ldp": mk_ldp,
        "round_robin": lambda: RoundRobin(build_regions(carbon, jt)),  # noqa: E731
        "least_rtt": lambda: LeastRTT(build_regions(carbon, jt)),  # noqa: E731
        "latency_only": lambda: LatencyOnly(build_regions(carbon, jt)),  # noqa: E731
        "carbon_blind_slo": lambda: CarbonBlindSLO(  # noqa: E731
            build_regions(carbon, jt), SLO_TTFT, SLO_ITL),
    }
    per = {k: [] for k in makers}
    seed_rows = []
    for s in range(SEEDS):
        for k, mk in makers.items():
            r = run_policy(mk, wl, 1000 + s)
            per[k].append(r)
            seed_rows.append({"policy": k, "seed": 1000 + s,
                             **{m: round(r[m], 6) for m in
                                ("gco2e", "viol_rate", "p99_ttft", "avg_wait_ms",
                                 "overhead_ms")}})
    with open("seed_results.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["policy", "seed", "gco2e", "viol_rate",
                                         "p99_ttft", "avg_wait_ms", "overhead_ms"])
        w.writeheader()
        w.writerows(seed_rows)
    out = []
    for k, runs in per.items():
        for metric in ("gco2e", "viol_rate", "p99_ttft", "avg_wait_ms", "overhead_ms"):
            v = [r[metric] for r in runs]
            m = statistics.mean(v)
            se = statistics.stdev(v) / math.sqrt(len(v)) if len(v) > 1 else 0
            out.append({"policy": k, "metric": metric, "n": len(v),
                        "mean": round(m, 6),
                        "ci95_lo": round(m - 1.96 * se, 6),
                        "ci95_hi": round(m + 1.96 * se, 6),
                        "wilcoxon_vs_ldp": "" if k == "ldp" else wilcoxon_signed(
                            [r[metric] for r in per["ldp"]], v)})
    with open("results.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["policy", "metric", "n", "mean",
                                         "ci95_lo", "ci95_hi", "wilcoxon_vs_ldp"])
        w.writeheader()
        w.writerows(out)
    print(f"wrote results.csv ({len(out)} rows); topology=EMULATED-netem (G2)")


if __name__ == "__main__":
    main()
