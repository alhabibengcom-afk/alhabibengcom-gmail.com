"""اختبارات مقابل حسابات يدوية."""
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ecp203 import design_beam, design_column, design_isolated_footing, flexural_capacity  # noqa: E402
from ecp203.beam import cmax_over_d, design_flexure, design_shear  # noqa: E402
from ecp203.column import axial_capacity  # noqa: E402
from ecp203.footing import punching_strength  # noqa: E402
from ecp203.report import Report  # noqa: E402


def test_cmax_fy400():
    # 2/3 × 600/(600 + 347.8) = 0.422
    assert cmax_over_d(400) == pytest.approx(0.422, abs=1e-3)


def test_flexure_hand_calc():
    # b=250, d=557, fcu=30, fy=400, Mu=220 → a=134.0, As=1290.9
    r = design_flexure(250, 600, 30, 400, -220, d=557, rep=Report("t"))
    assert r["As_req_mm2"] == pytest.approx(1290.9, abs=1)


def test_flexure_capacity_matches_design():
    r = design_flexure(250, 600, 30, 400, -220, d=557, rep=Report("t"))
    Mu, _ = flexural_capacity(250, 557, 30, 400, r["As_req_mm2"])
    assert Mu == pytest.approx(220, rel=0.01)


def test_doubly_reinforced_when_needed():
    r = design_flexure(250, 500, 25, 400, 330, d=450, rep=Report("t"))
    assert r["As_comp_mm2"] > 0.1 * r["As_design_mm2"]


def test_min_steel_governs_small_moment():
    r = design_flexure(250, 600, 30, 400, -10, d=557, rep=Report("t"))
    assert r["As_design_mm2"] == r["As_min_mm2"]


def test_shear_stirrups():
    # qu = 210e3/(250×557)=1.508 ; qcu,cr=0.12√20=0.537 ; qsu=0.971
    rep = Report("t")
    r = design_shear(250, 557, 30, 240, 210, rep=rep)
    assert r["qu_N_mm2"] == pytest.approx(1.508, abs=1e-3)
    assert rep.ok


def test_shear_section_too_small():
    rep = Report("t")
    design_shear(200, 300, 25, 240, 400, rep=rep)
    assert not rep.ok


def test_axial_capacity_eq_4_12a():
    # 0.35×30×(180000−1608) + 0.67×400×1608
    assert axial_capacity(180000, 1608, 30, 400) / 1e3 == pytest.approx(2304.2, abs=0.5)


def test_column_design_is_safe():
    rep = design_column(300, 600, 30, 400, Pu=2400, Mx=120, Hex=3200, Hey=3200)
    assert rep.ok


def test_column_overloaded():
    rep = design_column(250, 250, 25, 400, Pu=5000)
    assert not rep.ok


def test_punching_strength():
    s = math.sqrt(25 / 1.5)
    q, _ = punching_strength(25, 459, 3636, 300, 600)
    assert q == pytest.approx(min(0.316 * s * 1.0, 0.316 * s), abs=1e-3)


def test_footing_example():
    rep = design_isolated_footing(300, 600, D=1100, L=450, q_allow=200, fcu=25, fy=400)
    assert rep.ok
    assert rep.results["B × L × h"].startswith("2800 × 3100")


def test_beam_report_renders():
    md = design_beam(250, 600, 30, 400, Mu_pos=180, Mu_neg=220, Qu=210).to_markdown()
    assert "خطوات الحساب" in md and "تحقق من PDF" in md
