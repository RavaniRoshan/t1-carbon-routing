# Carbon-Aware, SLO-Constrained Routing of LLM Inference

Queue-aware Lyapunov routing across geo-distributed regions: **0.00760 gCO2e/1k tokens at 0.17% SLO violations** on an Azure production workload (40k-request reservoir sample) — 37–63% less carbon than round-robin, latency-only, and least-RTT baselines.

[![router-test](https://github.com/RavaniRoshan/t1-carbon-routing/actions/workflows/router-test.yml/badge.svg)](https://github.com/RavaniRoshan/t1-carbon-routing/actions/workflows/router-test.yml)
[![eval-run](https://github.com/RavaniRoshan/t1-carbon-routing/actions/workflows/eval-run.yml/badge.svg)](https://github.com/RavaniRoshan/t1-carbon-routing/actions/workflows/eval-run.yml)
[![carbon-pull](https://github.com/RavaniRoshan/t1-carbon-routing/actions/workflows/carbon-pull.yml/badge.svg)](https://github.com/RavaniRoshan/t1-carbon-routing/actions/workflows/carbon-pull.yml)

## Results

Measured GPU energy (NVML counters, 2×T4, N=30/cell) varies **951%** across batch/context, which is what makes routing worthwhile. Headline replay (Azure trace, real UK grid carbon, N=30 seeds, 95% CIs, paired Wilcoxon):

| Policy | gCO2e/1k | Viol | p99 TTFT |
|---|---|---|---|
| **LDP (ours)** | 0.0076 [0.0075, 0.0077] | 0.17% | 140.7 ms |
| Round-robin | 0.0121 | 0.57% | 117.7 ms |
| Least-RTT | 0.0205 | 95.07% | 15258.6 ms |
| Latency-only | 0.0167 | 0.13% | 106.0 ms |

Savings hold at 57%/56%/15% under 0.5×/1×/2× RTT scaling and move <1pt under ±25% carbon-signal noise. Full numbers in `paper/main.pdf` (4pp IEEE, Typst).

## How it fits together

Heavy work runs **online-only**: GPU sweeps on Kaggle, CPU replay on Actions. Nothing here needs a local GPU.

```text
kaggle/rq1-*  (workspace) ── T4 NVML energy sweeps ──▶ data/j_per_token.csv
UK Carbon Intensity API ── Actions carbon-pull ──────▶ data/carbon_snapshot.json
data/ + eval/sim.py ────── Actions eval-run (N=30) ──▶ results.csv
paper/gen_tables.py ── CSVs ──▶ tables/*.typ + figs/*.typ ──▶ main.pdf
```

- `router/` — queue-aware Lyapunov router (`ldp.py`: hard SLO feasibility filter, then `V·c·e + w` among feasible; min-regret fallback with debt accounting) plus baselines (`baselines.py`).
- `eval/` — Azure-trace replay harness (`sim.py`), RTT/noise sensitivity (`sensitivity.py`), carbon–latency Pareto (`pareto.py`).
- `data/` — measured inputs: per-token joules, latency model (ITL 34.36 ms), carbon snapshot.
- `evidence/` — vendored primary datasets the paper cites (`rq1/`: NVML joules + summaries; `eval/`: headline, seeds, sensitivity, pareto CSVs).
- `paper/` — Typst source (`charged-ieee` 0.1.4, `akatable`, `fletcher`, `cetz-plot`); tables/figures are generated, never hand-edited.
- `tests/` — router unit tests (5/5 green in CI).

> [!NOTE]
> Topology is **netem-only (emulated RTTs)**: no cloud multi-region access, so RTTs are shaped (95/55/10 ms) and labeled emulated throughout the paper. Arrival auto-tuning targets ρ = 0.7; regions are an 8-slot service model with no ITL inflation under concurrency (stated conservative limitation).

## Quickstart

```bash
python3 -m pytest tests/ -q   # router unit tests
python3 eval/sim.py            # CPU replay, writes results.csv + seed_results.csv
```

Paper (Typst 0.15.1, fonts embedded via `--font-path`):

```bash
python3 paper/gen_tables.py
python3 paper/verify_numbers.py   # fails the build if any prose number diverges from CSVs
typst compile --font-path paper/fonts paper/main.typ paper/main.pdf
```

GPU sweeps live in the research workspace (`kaggle/` kernels, pushed via `kaggle kernels push`); enable GPU + internet in the Kaggle UI, then copy results into `data/`. Carbon refresh and novelty sweeps run on dispatch (`carbon-pull.yml`, `novelty-sweep.yml`).

## Evidence map

| Claim | Source |
|---|---|
| 951% J/token spread, fp16 + quant | `evidence/rq1/summary.csv`, `evidence/rq1/summary_quant.csv` |
| 0.00760 gCO2e/1k, 0.17% viol | `evidence/eval/results.csv` (+ per-seed `seed_results.csv`) |
| RTT/noise sensitivity | `evidence/eval/sensitivity.csv` |
| V-invariant Pareto frontier | `evidence/eval/pareto.csv` |

> [!WARNING]
> On T4 with emulated (bitsandbytes) kernels, int8 costs 2.9–3.5× fp16 energy per token and int4 costs 1.1–1.4× — quantization-enabled demand response must budget dequantization overhead on this hardware class. Native FP8 paths may differ.
