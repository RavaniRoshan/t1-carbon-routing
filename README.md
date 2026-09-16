# T1 carbon-aware SLO-constrained LLM routing — online evidence repo

Online-only execution (local setup is not a compute target).
G2 fired 2026-09-16: no GCP access → netem-only topology, venue target IC2E / IEEE Access.

- GPU energy sweeps: Kaggle (`kaggle/rq1-pilot` sources mirrored here)
- CPU farm + scheduling: GitHub Actions (this repo)
- Topology: netem shaping validated against published inter-region RTTs (no Cloud Run)
- Carbon: UK CI API + ElectricityMaps pulls via Actions
- Goal state lives in the research workspace (`.opencode/goals/`), evidence lands in `evidence/`
