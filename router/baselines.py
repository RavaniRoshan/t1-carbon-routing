"""Baselines, queue-aware interface: route(regions, cin, cout, now, lat).
All share RegionState/commit so queueing consequences hit every policy honestly.
"""
from .ldp import commit, predict, service_ms


class RoundRobin:
    def __init__(self, regions):
        self.regions = {r.name: r for r in regions} if not isinstance(
            regions, dict) else regions
        self.names = list(self.regions)
        self.i = 0

    def route(self, regions, cin, cout, now, lat):
        r = self.regions[self.names[self.i % len(self.names)]]
        self.i += 1
        ttft, itl, wait = predict(r, cin, cout, now, lat)
        commit(r, now, wait, service_ms(cin, cout, lat))
        return r.name, False, wait


class LeastRTT:
    def __init__(self, regions):
        self.regions = {r.name: r for r in regions} if not isinstance(
            regions, dict) else regions

    def route(self, regions, cin, cout, now, lat):
        r = min(self.regions.values(), key=lambda x: x.rtt_ms)
        ttft, itl, wait = predict(r, cin, cout, now, lat)
        commit(r, now, wait, service_ms(cin, cout, lat))
        return r.name, False, wait


class LatencyOnly:
    """Carbon-blind, SLO-blind: fastest predicted TTFT. Violates under load."""

    def __init__(self, regions):
        self.regions = {r.name: r for r in regions} if not isinstance(
            regions, dict) else regions

    def route(self, regions, cin, cout, now, lat):
        best = min(regions, key=lambda r: predict(r, cin, cout, now, lat)[0])
        ttft, itl, wait = predict(best, cin, cout, now, lat)
        commit(best, now, wait, service_ms(cin, cout, lat))
        return best.name, False, wait


class CarbonBlindSLO:
    def __init__(self, regions, slo_ttft, slo_itl):
        self.regions = {r.name: r for r in regions} if not isinstance(
            regions, dict) else regions
        self.slo_ttft, self.slo_itl = slo_ttft, slo_itl

    def route(self, regions, cin, cout, now, lat):
        feas = [r for r in regions
                if predict(r, cin, cout, now, lat)[0] <= self.slo_ttft
                and predict(r, cin, cout, now, lat)[1] <= self.slo_itl]
        pool = feas or list(regions)
        best = min(pool, key=lambda r: predict(r, cin, cout, now, lat)[0])
        ttft, itl, wait = predict(best, cin, cout, now, lat)
        commit(best, now, wait, service_ms(cin, cout, lat))
        return best.name, (not feas), wait
