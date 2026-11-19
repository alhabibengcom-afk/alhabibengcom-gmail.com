"""اختبارات محرّك الإطار المكافئ وتصميم السقف الكامل."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aci318 import design_pt_floor  # noqa: E402
from aci318.floor_pt import _profile  # noqa: E402
from ecp203 import design_flat_slab_floor  # noqa: E402
from ecp203.efm import Frame, Support  # noqa: E402
from ecp203.floor_flat import envelope  # noqa: E402
from ecp203.grid import Grid  # noqa: E402


def _pin():
    return Support(c1=1e-4, c2=1e-4, H_below=None, H_above=None)


def test_continuous_beam_textbook():
    f = Frame([6, 6, 6], l2=6, h=0.2, supports=[_pin() for _ in range(4)]).solve()
    M, R, _ = f.combine([1, 1, 1])
    assert M[f.node_at(6.0)] == pytest.approx(-0.1 * 36, abs=1e-3)
    assert list(R) == pytest.approx([2.4, 6.6, 6.6, 2.4], abs=1e-3)


def test_fixed_end_with_stiff_spring():
    class F(Frame):
        def kec(self, s):
            return 1e7
    f = F([6], l2=6, h=0.2, supports=[_pin(), _pin()]).solve()
    M, _, Mc = f.combine([1])
    assert M[1] == pytest.approx(-3.0, abs=1e-3)
    assert abs(Mc[0]) == pytest.approx(3.0, abs=1e-3)


def test_static_moment_between_faces():
    """مجموع متوسط عزمي الوشين + الموجب = w·ln²/8 (من غير ترتيب حمل حي)."""
    g = Grid([0, 6, 12, 18], [0, 6, 12, 18], 240, (500, 500))
    _, _, fr = g.frames("x")[1]
    env, _, _ = envelope(fr, 10.0, 0.0, [[0, 0, 0]])
    mL, mp, mR = env[1]
    ln = 6 - 0.5
    assert (abs(mL) + abs(mR)) / 2 + mp == pytest.approx(10 * ln ** 2 / 8, rel=0.01)


def test_column_override_is_one_based():
    g = Grid([0, 6, 12], [0, 6, 12], 240, (500, 500), {"2,2": [800, 800]})
    assert g.col_size(1, 1) == (800, 800)
    assert g.col_size(0, 0) == (500, 500)


def test_flat_slab_floor_example():
    rep = design_flat_slab_floor([0, 6, 12, 18], [0, 6, 12, 18], 240, 2.5, 3.0, fcu=30)
    assert rep.ok
    assert rep.results["max_punching_ratio"] < 1.0


def test_flat_slab_too_thin_fails():
    rep = design_flat_slab_floor([0, 8, 16], [0, 8, 16], 180, 2.5, 3.0)
    assert not rep.ok


def test_pt_profile_and_force():
    g = Grid([0, 8, 16, 24], [0, 8, 16, 24], 250, (600, 600))
    _, _, fr = g.frames("x")[1]
    e_sup, e_mid, a = _profile(fr, 0.25, 0.045, 0.045)
    assert e_sup[0] == 0 and e_sup[1] == pytest.approx(-0.08)
    assert a == pytest.approx([0.12, 0.16, 0.12])
    # P = 0.8 × (25×0.25×8) × 8² / (8 × 0.12)
    assert 0.8 * 50 * 64 / (8 * 0.12) == pytest.approx(2666.7, abs=0.1)


def test_pt_floor_example_passes():
    rep = design_pt_floor([0, 8, 16, 24], [0, 8, 16, 24], 260, 2.5, 3.0, col=(600, 600),
                          col_override={"2,2": [700, 700], "2,3": [700, 700], "3,2": [700, 700], "3,3": [700, 700]})
    assert rep.results["sections_checked"] == 72
    assert rep.ok


def test_pt_floor_punching_fails_for_small_columns():
    rep = design_pt_floor([0, 8, 16, 24], [0, 8, 16, 24], 250, 2.5, 3.0, col=(600, 600))
    assert not rep.ok
