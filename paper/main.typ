#import "@preview/charged-ieee:0.1.4": ieee
#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge
#show: ieee.with(
  title: [Carbon-Aware, SLO-Constrained Routing of LLM Inference Across Geo-Distributed Regions],
  authors: ((name: "Ravani Roshan", organization: [Independent Research]),),
  abstract: [Geo-distributed LLM serving can cut operational carbon by routing requests to cleaner grids, but only if latency SLOs survive the detour and the carbon numbers rest on measured GPU energy rather than TDP estimates. We measure energy per token on real GPUs (NVML cumulative counters, N=30/cell), finding a 951% spread across batch and context that justifies energy-aware routing, and showing emulated int8/int4 quantization costs 1.1--3.5x more energy than fp16 on T4 hardware. Our queue-aware Lyapunov drift-plus-penalty router applies a hard SLO feasibility filter first and prices carbon against queue delay among feasible regions. Replaying 40000 Azure production requests against real UK grid carbon traces, the router records 0.00760 gCO2e per 1k tokens at 0.17% SLO violations: 37% less carbon than round-robin, 55% less than latency-only routing, and 63% less than least-RTT routing, which collapses to 95% violations under load. Savings persist at 57%/56%/15% under 0.5x/1x/2x RTT scaling and are robust to +-25% carbon-signal noise. All datasets, router code, and harnesses are open.],
  index-terms: ("LLM inference", "carbon-aware computing", "geo-distributed systems", "SLO", "Lyapunov optimization"),
  paper-size: "us-letter",
  bibliography: bibliography("refs.bib", style: "ieee"),
)
#set math.equation(numbering: "(1)")

= Introduction
Large-language-model inference is shifting from a latency-and-cost problem to an energy-and-carbon problem @dynamollm @lldsynth. Because grids differ in carbon intensity by an order of magnitude across regions and hours @emaps, routing a request to a cleaner grid can cut its footprint without changing the model or the answer. The idea is old in serverless scheduling @greencourier @casper @caribou; the open question is whether it survives contact with autoregressive LLM serving: batch- and context-dependent energy per token, millisecond TTFT/ITL SLOs, queueing under load, and stale carbon signals.

Closest prior halves do not combine. Live marginal-emission GPU routing demonstrates the measurement path but disclaims SLO coverage @bernhard. SLO-constrained carbon routing exists across model tiers with estimated energy and no geo dimension @gar, and across serverless functions without LLM inference @slarouter. Thermal schedulers optimize single datacenters @etcinfer; keep-alive controllers optimize single regions @lacerl; planners simulate deployment alternatives without routing @infact. Our conjunction --- per-request carbon-aware routing of autoregressive inference across geo-distributed regions under a hard SLO gate with measured GPU energy---was absent in our September 2026 sweep (@tab:rq2 and @sec:related).

We make four contributions. (1) A measurement protocol and dataset: NVML cumulative-counter joules with >=5 s windows, N=30 per cell, median/IQR/95% CI, on 2xT4 GPUs, settling the contested quantization question on this hardware class. (2) A queue-aware Lyapunov router with a hard feasibility filter: it never knowingly violates an SLO and prices carbon against queue delay only among feasible regions. (3) An evaluation on 40000 Azure production requests with real grid carbon, N=30 seeds, 95% CIs, and paired Wilcoxon tests against five baselines, plus RTT/noise sensitivity and a carbon--latency Pareto. (4) Open artifacts: datasets, router, and harnesses.

= Background
== Serving metrics
We use time-to-first-token (TTFT), inter-token latency (ITL), and DistServe-style goodput: a request counts only when all its SLOs hold @ietfbench. Our serving envelope (Qwen2.5-0.5B, fp16, T4) measures ITL 34.36 ms and TTFT of a few ms at batch 1; end-to-end for 64 output tokens is ~2.2 s. Regional RTT (10--95 ms shaped) and queue wait therefore dominate TTFT SLO compliance at a 140 ms threshold.

== Carbon signals
Average intensity (attributional, flow-traced gCO2eq/kWh @emaps) is mandatory for Scope 2 reporting; marginal intensity (consequential MOER @watttime) guides load-shift decisions. Optimizing one can raise the other, so we report the average-signal configuration and require the same signal for scheduling and accounting.

== Lyapunov routing
Drift-plus-penalty control minimizes $V dot p + Delta$ per decision, where $p$ is the carbon penalty, $Delta$ the virtual-queue drift, and $V$ trades them. Classical formulations pick among all actions; we restrict the choice to the SLO-feasible set first, which we show dominates soft carbon--latency weighting on violations, consistent with recent ablations @slarouter.

= Measurement Methodology (RQ1)
Energy comes from `nvmlDeviceGetTotalEnergyConsumption` deltas across synchronized windows, never from averaged power polling, following community best practice @zeus. Direct NVML polling reaches 266--274 Hz; repeated `nvidia-smi` subprocess polling manages only 5.3 Hz and cannot resolve short decodes. Windows under 2 s show counter-granularity zeros; we use warmup, 5 s cooldowns, and >=5 s measured windows (5/5 positive deltas, median 337.65 J per 5 s matmul window). Each sweep cell uses N=30 with median, IQR, and normal-approx 95% CI. Host energy is modeled with GPU share cited at 91--92% under load.

= Router Design
#figure(
  diagram(
    node((0,0), [Requests]),
    node((2.2,0), [Feasibility\ filter]),
    node((4.6,0), [LDP\ min $V dot "carbon" dot e + w$]),
    node((4.6,-1.2), [Fallback]),
    node((2.2,-1.2), [Regions]),
    edge((0,0), (2.2,0), [SLO]),
    edge((2.2,0), (4.6,0), [feasible]),
    edge((2.2,0), (4.6,-1.2), [none]),
    edge((4.6,0), (2.2,-1.2), [commit]),
  ),
  caption: [Router pipeline: hard SLO filter, Lyapunov choice among feasible, min-regret fallback with debt accounting.],
) <fig:router>

Each region holds an 8-slot service model (continuous-batching approximation; no ITL inflation under concurrency, a stated conservative limitation). Predicted TTFT adds RTT, queue wait, and measured prefill; feasibility is decided against p99 TTFT/ITL SLOs. Scores follow

$ "score"(r) = V dot c_r dot e_r + w_r $

with $c_r$ regional carbon, $e_r$ request joules from the measured table, and $w_r$ queue wait. Violations of the filter are never knowingly taken; when no region is feasible the router takes min-regret (least excess TTFT) and grows a debt queue. $V$ prices carbon against delay.

= Evaluation Setup
Workload: 40000 requests reservoir-sampled from the Azure LLM Inference Trace 2024 conversation and code splits (CC-BY) @azuretrace @dynamollm. Carbon: UK Carbon Intensity API 18-region forecast snapshot. Topology: three shaped regions (netem-only; no Cloud Run access, stated openly): green/far (95 ms), mid (55 ms), dirty/near (10 ms) with 0.4x/1.0x/1.8x carbon. Arrival: Poisson auto-tuned to $rho = 0.7$ against measured service. Baselines: round-robin, least-RTT, latency-only, carbon-blind SLO, plus the soft-weighted ablation family. Statistics: N=30 seeds, 95% CIs, paired Wilcoxon signed-rank LDP versus each baseline. SLOs: p99 TTFT 140 ms, ITL 40 ms.

= Results
== RQ1: energy per token varies 951%
#include "tables/rq1_energy.typ"
Batch dominates: 1.39 J/tok at B=1/C=128 falls to 0.14 at B=16/C=128; context adds 8--56% within a batch. The max/min spread is 951%, far above the 10% gate that would have collapsed the paper to a characterization study.

== Quantization costs energy here
#include "tables/rq1_quant.typ"
On T4 with emulated (bitsandbytes) kernels, int8 costs 3.0--3.5x fp16 per token and int4 costs 1.1--1.4x; end-to-end latency confirms it (int8 B=8: 8.8 s vs fp16 2.1 s). Quantization-enabled demand response @quantdr must therefore budget dequantization overhead on this hardware class; native FP8 paths may differ.

== RQ2: carbon down 37--63% at near-zero violations
#include "tables/rq2_headline.typ"
LDP records 0.00760 gCO2e/1k tokens at 0.17% violations: -37.4% vs round-robin (p=0.0), -54.6% vs latency-only (p=0.0, violations statistically tied at p=1.0), -62.9% vs least-RTT (p=0.0). Least-RTT is the cautionary tale: concentrating load on the nearest region explodes queues (p99 15.3 s, 95.07% violations). Routing overhead is ~1 us per request.

== RQ3: RTT dominates, noise does not
#include "tables/rq3_sens.typ"
Halving RTT lifts savings to ~57%; doubling RTT cuts them to ~15% with violations rising to 5.5% as the green/far region turns infeasible. +-25% carbon-signal noise moves savings by under a point at 0.13% violations: feasibility, not forecast precision, is the binding constraint in this shape.

== RQ4: p99 tracks each SLO
#include "tables/rq4_pareto.typ"
Across SLOs 100--180 ms, p99 TTFT lands just under each threshold (99.6/117.6/137.0/176.3) at ~0.1% violations while carbon falls. We report honestly that $V in [0.1, 5]$ is decision-invariant under the hard filter at this load: the filter, not the knob, does the work---consistent with hard-filtering beating soft weighting @slarouter and simple policies capturing most shifting gains.

= Threats to Validity
Netem-only topology (no multi-region cloud access) is the largest threat; RTTs are shaped and labeled emulated throughout, and third-party RTT validation is future work. Single-server 8-slot regions approximate continuous batching without ITL inflation. Kaggle T4 workers are shared; host energy is modeled. The TTFT streamer artifact (1--2 ms first-`put`) was discarded with TTFT derived as e2e minus decode. Violation-rate CIs near zero show normal-approx negative bounds, clipped at zero in prose. Round-robin carbon CIs are degenerate by construction (request-invariant metric with fixed cycle counts).

= Related Work <sec:related>
Serverless carbon routing (@greencourier @casper @slarouter @casa) and geospatial workflow shifting @caribou motivate the filter-then-minimize discipline we adopt. LLM-specific halves --- measured-energy geo-routing without SLOs @bernhard, SLO routing across model tiers without geo or measured energy @gar, thermal single-site control @etcinfer, temporal keep-alive @lacerl, tier-based function calling @edgefunc, planning tools @infact, attribution methods @jouleshare, and the llm-d synthesis @lldsynth --- each drop at least one of our four conjuncts. Demand response via quantization @quantdr is the closest efficiency lever and, per our @tab:quant, must clear the dequantization hurdle first.

= Conclusion
Measured GPU energy varies enough to route on; a hard feasibility filter plus Lyapunov pricing converts that variation into 37--63% carbon cuts at near-zero SLO violations on production traces, robust to signal noise and bounded by RTT feasibility. Artifacts are open for replication and extension to real multi-region deployments.
