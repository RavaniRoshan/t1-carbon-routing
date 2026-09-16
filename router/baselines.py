"""Baselines for Phase 3: round-robin, least-loaded (least RTT), latency-only,
carbon-blind SLO routing. Same interface as LDPRouter.route. CPU-only."""


class RoundRobin:
    def __init__(self, regions):
        if isinstance(regions, dict):
            self.regions = regions
            self.names = list(regions)
        else:
            self.names = list(regions)
            self.regions = {n: None for n in self.names}
        self.i = 0

    def route(self, *a):
        n = self.names[self.i % len(self.names)]
        self.i += 1
        return n, False


class LeastLoaded:
    def __init__(self, regions):
        self.regions = {r.name: r for r in regions} if not isinstance(regions, dict) else regions

    def route(self, *a):
        return min(self.regions.values(),
                   key=lambda r: r.rtt_ms).name, False


class LatencyOnly:
    def __init__(self, router):
        self.router = router  # reuse predict()

    @property
    def regions(self):
        return self.router.regions

    def route(self, ti, to):
        best = min(self.router.regions.values(),
                   key=lambda r: sum(self.router.predict(r, ti, to)))
        return best.name, False


class CarbonBlindSLO:
    def __init__(self, router):
        self.router = router

    @property
    def regions(self):
        return self.router.regions

    def route(self, ti, to):
        feas = [r for r in self.router.regions.values()
                if all(v <= s for v, s in zip(
                    self.router.predict(r, ti, to),
                    (self.router.slo_ttft, self.router.slo_itl)))]
        pool = feas or list(self.router.regions.values())
        # carbon-blind: fastest feasible (or fastest overall), NOT min-carbon
        best = min(pool, key=lambda r: sum(self.router.predict(r, ti, to)))
        return best.name, (not feas)
