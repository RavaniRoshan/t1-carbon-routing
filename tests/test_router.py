"""Synthetic unit test (fast, CPU): LDP routes green-feasible, debt grows on violation."""
from router.ldp import LDPRouter, Region


def test_green_feasible_wins():
    regs = [Region("green", carbon=50, rtt_ms=20, j_per_token=0.5),
            Region("dirty", carbon=400, rtt_ms=10, j_per_token=0.5)]
    r = LDPRouter(regs, slo_ttft_ms=500, slo_itl_ms=100, V=1.0)
    name, viol = r.route(128, 64)
    assert name == "green" and not viol, (name, viol)


def test_debt_grows_when_nothing_feasible():
    regs = [Region("far", carbon=50, rtt_ms=900, j_per_token=0.5)]
    r = LDPRouter(regs, slo_ttft_ms=100, slo_itl_ms=20, V=1.0)
    r.route(512, 64)
    assert r.debt > 0
