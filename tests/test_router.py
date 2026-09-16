"""Synthetic unit tests (fast, CPU) for queue-aware router."""
from router.baselines import CarbonBlindSLO, LatencyOnly, LeastRTT, RoundRobin
from router.ldp import LDPRouter, RegionState, predict

LAT = {"ttft_base_ms": 2.0, "ttft_per_input_ms": 0.005, "itl_ms": 34.36}


def mk_regs():
    return [RegionState("green", 50, 95, 0.5),
            RegionState("dirty", 400, 10, 0.5)]


def test_green_feasible_wins():
    r = LDPRouter(mk_regs(), 500, 100, V=1.0)
    name, viol, _ = r.route(mk_regs(), 128, 64, 0.0, LAT)
    assert name == "green" and not viol, (name, viol)


def test_hard_filter_never_knowingly_violates():
    # green TTFT at C=512 = 95+2+2.56 = 99.56; SLO 50 kills it even at huge V
    r2 = LDPRouter(mk_regs(), 50, 40, V=1000.0)
    regs3 = mk_regs()
    name2, viol2, _ = r2.route(regs3, 512, 64, 0.0, LAT)
    assert name2 == "dirty" and not viol2, (name2, viol2)


def test_queue_deflects_when_green_busy():
    regs = mk_regs()
    regs[0].slots = [100000.0] * len(regs[0].slots)  # green jammed
    r = LDPRouter(regs, 5000, 100, V=0.0001)  # tiny V -> wait dominates
    name, viol, _ = r.route(regs, 128, 64, 0.0, LAT)
    assert name == "dirty", name


def test_baselines_run():
    for cls in (RoundRobin, LeastRTT, LatencyOnly):
        regs = mk_regs()
        p = cls(regs)
        p.route(regs, 128, 64, 0.0, LAT)
    regs = mk_regs()
    CarbonBlindSLO(regs, 500, 100).route(regs, 128, 64, 0.0, LAT)


def test_predict_queueing():
    regs = mk_regs()
    regs[0].slots = [500.0] * len(regs[0].slots)
    ttft, itl, wait = predict(regs[0], 128, 64, 0.0, LAT)
    assert wait == 500.0 and ttft > 500.0 and itl == 34.36
