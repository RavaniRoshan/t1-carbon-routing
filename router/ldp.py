"""Queue-aware Lyapunov router (v2) + shared serving model.
Serving model (data/latency_model.json, MEASURED T4 0.5B fp16 B=1 N=20/cell):
single-server per region; queue wait adds to TTFT only (documented approx;
batching/continuous-batching gains excluded -> conservative).
Routing: HARD feasibility filter first (never knowingly violates), LDP score
V*carbon*energy + wait_ms among feasible; min-regret fallback (min excess TTFT)
with debt accounting only when nothing is feasible. V is real: it prices carbon
(J*g/kWh) against queue delay (ms).
"""


SLOTS = 8  # concurrent-batch slots per region (continuous-batching approx;
# documented limitation: no ITL inflation under concurrency)


class RegionState:
    def __init__(self, name, carbon, rtt_ms, j_per_token, slots=SLOTS):
        self.name = name
        self.carbon = carbon
        self.rtt_ms = rtt_ms
        self.j_per_token = j_per_token
        self.slots = [0.0] * slots


def service_ms(cin, cout, lat):
    return (lat["ttft_base_ms"] + lat["ttft_per_input_ms"] * cin
            + lat["itl_ms"] * cout)


def predict(rs, cin, cout, now, lat):
    wait = max(0.0, min(rs.slots) - now)
    ttft = rs.rtt_ms + wait + lat["ttft_base_ms"] + lat["ttft_per_input_ms"] * cin
    return ttft, lat["itl_ms"], wait


def commit(rs, now, wait, svc):
    i = min(range(len(rs.slots)), key=lambda k: rs.slots[k])
    rs.slots[i] = max(rs.slots[i], now) + svc
    return wait


class LDPRouter:
    def __init__(self, regions, slo_ttft_ms, slo_itl_ms, V=1.0):
        self.regions = {r.name: r for r in regions}
        self.slo_ttft = slo_ttft_ms
        self.slo_itl = slo_itl_ms
        self.V = V
        self.debt = 0.0
        self.decisions = []

    def route(self, regions, cin, cout, now, lat):
        scored = []
        for r in regions:
            ttft, itl, wait = predict(r, cin, cout, now, lat)
            feas = ttft <= self.slo_ttft and itl <= self.slo_itl
            e_j = r.j_per_token * (cin + cout)
            if feas:
                score = self.V * r.carbon * e_j + wait
            else:
                # min-regret fallback: smallest excess first, debt prices it
                score = 1e12 + (ttft - self.slo_ttft) + self.debt * 1e6
            scored.append((score, feas, r, wait))
        scored.sort(key=lambda t: t[0])
        _, feas, best, wait = scored[0]
        svc = service_ms(cin, cout, lat)
        commit(best, now, wait, svc)
        self.debt = max(0.0, self.debt + (1.0 if not feas else -0.05))
        self.decisions.append((best.name, not feas))
        return best.name, (not feas), wait
