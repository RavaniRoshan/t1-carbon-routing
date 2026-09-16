"""Lyapunov drift-plus-penalty carbon router (skeleton, CPU-only).
Per-request: feasible set {regions with predicted TTFT/ITL <= SLO}
then min carbon. Virtual queue tracks SLO-debt; V trades carbon vs debt.
Latency/carbon models are injected (RQ1 summary.csv + carbon series),
never hardcoded. Full eval in Phase 3 task.
"""


class Region:
    def __init__(self, name, carbon, rtt_ms, j_per_token):
        self.name = name
        self.carbon = carbon  # gCO2eq/kWh at decision time
        self.rtt_ms = rtt_ms
        self.j_per_token = j_per_token


class LDPRouter:
    def __init__(self, regions, slo_ttft_ms, slo_itl_ms, V=1.0):
        self.regions = {r.name: r for r in regions}
        self.slo_ttft = slo_ttft_ms
        self.slo_itl = slo_itl_ms
        self.V = V
        self.debt = 0.0  # virtual SLO-debt queue
        self.decisions = []

    def predict(self, region, tokens_in, tokens_out):
        # Placeholder model: refined with RQ1 latency fits in Phase 2 task.
        # Returns (ttft_ms, itl_ms) estimates.
        base = 40.0 + region.rtt_ms
        ttft = base + 0.05 * tokens_in
        itl = 25.0 + 0.5 * (tokens_in / 512.0)
        return ttft, itl

    def route(self, tokens_in, tokens_out):
        scored = []
        for r in self.regions.values():
            ttft, itl = self.predict(r, tokens_in, tokens_out)
            feasible = ttft <= self.slo_ttft and itl <= self.slo_itl
            # drift-plus-penalty: V*carbon*energy + debt*violation_risk.
            # V knob is real: high V tolerates debt (carbon-first), low V
            # lets debt steer to feasible regions.
            score = self.V * r.carbon * r.j_per_token + self.debt * (0.0 if feasible else 1.0)
            scored.append((score, feasible, r))
        scored.sort(key=lambda t: t[0])
        _, feasible, best = scored[0]
        violated = not feasible
        self.debt = max(0.0, self.debt + (1.0 if violated else -0.05))
        self.decisions.append((best.name, violated))
        return best.name, violated
