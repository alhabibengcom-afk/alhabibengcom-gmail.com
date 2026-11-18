"""اختبارات البلاطات (ECP) والبوست تنشن (ACI) مقابل حسابات يدوية."""
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aci318 import check_pt_punching, check_pt_section  # noqa: E402
from aci318.pt_slab import beta1  # noqa: E402
from ecp203 import check_flat_slab_punching, design_one_way_slab, design_two_way_slab  # noqa: E402


def test_one_way_min_thickness_and_steel():
    rep = design_one_way_slab(3.6, 5.0, 2.0, "both_ends", fcu=25, fy=400)
    assert rep.results["t_mm"] == 90.0          # 3600/40
    assert rep.results["wu_kN_m2"] == 10.2       # 1.4×5 + 1.6×2
    assert rep.ok


def test_two_way_alpha_beta():
    rep = design_two_way_slab(4.5, 5.5, 5.5, 2.0, 2, 2)
    assert rep.results["r"] == pytest.approx(5.5 / 4.5, abs=1e-3)
    alpha = next(s.value for s in rep.steps if s.desc.startswith("معامل توزيع الحمل α"))
    assert alpha == pytest.approx(0.5 * 5.5 / 4.5 - 0.15)


def test_two_way_becomes_one_way():
    rep = design_two_way_slab(3.0, 7.0, 5.0, 2.0, 2, 2)
    assert "اتجاه واحد" in rep.title


def test_flat_slab_punching_hand_calc():
    rep = check_flat_slab_punching(500, 500, 250, 900, fcu=30)
    assert rep.results["qup"] == pytest.approx(1.653, abs=1e-3)
    assert rep.results["qcup"] == pytest.approx(0.316 * math.sqrt(20), abs=1e-3)
    assert not rep.ok


def test_beta1_table():
    assert beta1(25) == 0.85
    assert beta1(35) == pytest.approx(0.80)
    assert beta1(60) == 0.65


PT = dict(b=3500, h=250, fc=35, fci=25, Aps=1680, Pe=1600, Pi=1850, Pj=2300, e=75,
          M_D=120, M_SDL=45, M_L=70, M2=25, M_sw=120, region="positive", span=8.0)


def test_pt_section_service_stresses():
    rep = check_pt_section(**PT)
    ft, fb = (float(x) for x in rep.results["f_top/f_bot service (MPa)"].split(" / "))
    assert ft == pytest.approx(-1.829 - 3.840, abs=0.01)
    assert fb == pytest.approx(-1.829 + 3.840, abs=0.01)


def test_pt_section_min_steel_and_strength():
    rep = check_pt_section(**PT)
    assert rep.results["As_min_mm2"] == pytest.approx(1098, abs=3)   # Nc/(0.5fy)
    assert rep.results["fps_MPa"] == pytest.approx(952.4 + 70 + 145.8, abs=1)
    assert rep.results["Mu_kNm"] == pytest.approx(335.0)
    assert rep.ok


def test_pt_tension_exceeds_class_u():
    rep = check_pt_section(**{**PT, "M_L": 250})
    assert not rep.ok


def test_pt_negative_region_min_steel():
    rep = check_pt_section(**{**PT, "region": "negative", "e": -90, "M_D": -200, "M_SDL": -70,
                              "M_L": -110, "M_sw": -200, "M2": 25, "frame_width": 8000})
    assert rep.results["As_min_mm2"] == pytest.approx(0.00075 * 250 * 8000)


def test_pt_punching_caps_sqrt_fc():
    rep = check_pt_punching(600, 600, 250, 950, fc=35, fpc=1.8, Msc=60)
    assert rep.results["vu_MPa"] == pytest.approx(1.623, abs=2e-3)
    assert rep.results["phi_vc_MPa"] == pytest.approx(0.75 * (0.29 * 5.8 + 0.3 * 1.8), abs=1e-3)


def test_pt_punching_edge_falls_back():
    rep = check_pt_punching(600, 600, 250, 500, fc=35, fpc=1.8, location="edge")
    assert any("22.6.5.2" in n for n in rep.notes)
