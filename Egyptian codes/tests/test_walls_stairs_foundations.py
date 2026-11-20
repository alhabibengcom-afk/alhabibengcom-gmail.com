"""اختبارات الحوائط والسلالم والهوردي والقواعد المشتركة واللبشة مقابل حسابات يدوية."""
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ecp203 import (design_combined_footing, design_hollow_block_one_way, design_hollow_block_two_way,  # noqa: E402
                    design_raft, design_stair, design_wall)


def _step(rep, prefix):
    return next(s.value for s in rep.steps if s.desc.startswith(prefix))


def test_wall_simplified_capacity():
    rep = design_wall(200, 3.0, 4.0, 30, 400, Pu=900, Mu=12)
    # 0.8×0.35×30×200000×[1 − (2400/6400)²]
    assert _step(rep, "مقاومة الحائط") == pytest.approx(1443.75, abs=0.5)
    assert rep.ok


def test_wall_eccentric_uses_column_method():
    rep = design_wall(200, 3.0, 4.0, 30, 400, Pu=400, Mu=40)
    assert any("قطاع عمود" in s.desc for s in rep.steps)
    assert rep.ok


def test_wall_too_slender():
    rep = design_wall(150, 6.0, 4.0, 30, 400, Pu=300, end="pinned")
    assert not rep.ok   # λ = 40 > 30


def test_stair_loads():
    rep = design_stair(3.6, 160, 300, 160)
    th = math.atan(160 / 300)
    wD = 25 * 0.16 / math.cos(th) + 25 * 0.16 / 2 + 1.5
    assert rep.results["wu_kN_m2"] == pytest.approx(1.4 * wD + 1.6 * 3.0, abs=0.01)
    assert rep.ok


def test_stair_cantilever():
    rep = design_stair(1.2, 160, 300, 150, kind="cantilever")
    assert rep.results["top_per_m"]


def test_hollow_block_one_way():
    rep = design_hollow_block_one_way(5.5, 300, 50, 120, 400, 2.0, 2.0)
    assert rep.results["wu_kN_m2"] == pytest.approx(1.4 * (25 * 0.056 / 0.52 + 3.0) + 3.2, abs=0.01)
    assert rep.results["cross_ribs"] == 1
    assert rep.ok


def test_hollow_block_bad_dimensions():
    rep = design_hollow_block_one_way(5.0, 300, 40, 80, 800, 2.0, 2.0)
    assert not rep.ok


def test_hollow_block_two_way_runs():
    rep = design_hollow_block_two_way(5.0, 6.0, 300, 50, 120, 400, 2.0, 2.0)
    assert rep.results["rib_bottom_a"] and rep.results["rib_bottom_b"]


COMB = dict(col1={"a": 300, "b": 500, "D": 700, "L": 250}, col2={"a": 300, "b": 600, "D": 1000, "L": 400},
            spacing=4.0, q_allow=180, x1=0.25)


def test_combined_footing_geometry():
    rep = design_combined_footing(**COMB)
    assert rep.results["B × L × h"].startswith("2750 × 5300")
    assert rep.ok


def test_combined_footing_moments_close_to_uniform_hand_calc():
    rep = design_combined_footing(**COMB)
    Mneg = _step(rep, "أقصى عزم (شد علوي")
    w = 3420 / 5.3
    x0 = 1380 / w
    hand = -(w * x0 ** 2 / 2 - 1380 * (x0 - 0.25))
    assert Mneg == pytest.approx(hand, rel=0.03)


def test_raft_pressure_and_punching():
    cols = [{"x": x, "y": y, "c1": 500, "c2": 500, "D": 1200, "L": 400}
            for x in (0.5, 6.5, 12.5) for y in (0.5, 6.5, 12.5)]
    rep = design_raft(13, 13, cols, q_allow=150)
    # متماثلة → ضغط منتظم = (ΣP + W)/A
    W = 25 * rep.results["t_mm"] / 1000 * 169
    assert rep.results["q_max_service"] == pytest.approx((9 * 1600 + W) / 169, abs=0.2)
    assert rep.ok
