"""القواعد المشتركة واللبشة (الطريقة الجاسئة) - ECP 203-2020.

ECP 203 بيحكم التصميم الخرساني (الانحناء، القص، القص الثاقب، التسليح الأدنى).
توزيع ضغط التربة وجهدها المسموح من كود الأساسات 202 / تقرير التربة (مش موجود في
المرجع)، فالمكتبة بتفترض أساس جاسئ وتوزيع ضغط خطي — ده لازم يتراجع، وفي
اللبشات الكبيرة أو التربة الضعيفة الأدق تحليل بـ SAFE (Winkler) وتصميم الشرائح
بـ design_slab_strip.

الأحمال: أحمال تشغيل D و L (kN) لكل عمود. الإحداثيات بالمتر. الأبعاد بالمم.
"""
from __future__ import annotations

import math

from . import params as P
from .footing import punching_strength
from .report import Report
from .slab import strip_steel


def _rnd_up(x, step=0.05):
    return math.ceil(x / step - 1e-9) * step


def _punch(rep, name, Pu, qu, c1, c2, d, fcu, location):
    if location == "interior":
        A_in = (c1 + d) * (c2 + d)
        bo = 2 * (c1 + d) + 2 * (c2 + d)
    elif location == "edge":
        A_in = (c1 + d / 2) * (c2 + d)
        bo = 2 * (c1 + d / 2) + (c2 + d)
    else:
        A_in = (c1 + d / 2) * (c2 + d / 2)
        bo = (c1 + d / 2) + (c2 + d / 2)
    Qup = Pu - qu * A_in / 1e6
    qup = Qup * 1e3 / (bo * d)
    qcup, _ = punching_strength(fcu, d, bo, c1, c2, location)
    if rep:
        rep.step(f"القص الثاقب — {name} ({location})", "qup = (Pu − qu·A_in)/(bo·d)",
                 f"({Pu:.0f} − {qu:.1f}×{A_in/1e6:.3f})×10³/({bo:.0f}×{d:.0f})", qup, "N/mm²", P.REF_PUNCH)
        rep.check(f"qup ≤ qcup — {name}", qup, qcup, "N/mm²", P.REF_PUNCH)
    return qup <= qcup


# ------------------------------------------------------------------ قاعدة مشتركة
def design_combined_footing(col1, col2, spacing, q_allow, fcu=25, fy=400, x1=None, B=None, h=None,
                            cover=75.0, self_weight_factor=0.10, title=None):
    """col1 / col2: dict(a=..., b=..., D=..., L=...) — a عمودي على المحور، b في اتجاه المحور (mm)، الأحمال kN.
    spacing: بين محوري العمودين (m). x1: البروز من محور العمود الأول للحافة (m) — لو العمود على حد الملك
    دخّل x1 = b1/2000. q_allow: جهد التربة الصافي (kN/m²)."""
    rep = Report(title or "قاعدة مشتركة لعمودين — ECP 203-2020")
    P1s, P2s = col1["D"] + col1["L"], col2["D"] + col2["L"]
    Pu1 = P.LOAD_D * col1["D"] + P.LOAD_L * col1["L"]
    Pu2 = P.LOAD_D * col2["D"] + P.LOAD_L * col2["L"]
    rep.inputs = {"العمود 1": f"{col1['a']}×{col1['b']} mm ، D={col1['D']} L={col1['L']} kN",
                  "العمود 2": f"{col2['a']}×{col2['b']} mm ، D={col2['D']} L={col2['L']} kN",
                  "المسافة بين المحورين": f"{spacing} m", "q allow (صافي)": f"{q_allow} kN/m²", "fcu / fy": f"{fcu} / {fy}"}
    rep.step("أحمال التشغيل", "Ps = D + L", "", f"{P1s:.0f} / {P2s:.0f}", "kN")
    rep.step("الأحمال القصوى", "Pu = 1.4D + 1.6L", "", f"{Pu1:.0f} / {Pu2:.0f}", "kN", P.REF_LOADS)
    xr = rep.step("مكان المحصلة من محور العمود 1", "xr = P2·s/(P1 + P2)", f"{P2s}×{spacing}/({P1s}+{P2s})",
                  P2s * spacing / (P1s + P2s), "m")
    if x1 is None:
        x1 = max(col1["b"] / 2000 + 0.3, 0.5)
        rep.note(f"x1 مش مُدخل: اتفرض بروز {x1:.2f} م من محور العمود 1. لو العمود على حد الملك دخّل x1 = b1/2.")
    L = rep.step("طول القاعدة (المحصلة في المنتصف)", "L = 2(x1 + xr)", f"2({x1} + {xr:.3f})", _rnd_up(2 * (x1 + xr)), "m")
    if B is None:
        B = rep.step("عرض القاعدة", "B = (1+k)·Ps / (q·L)", f"{1+self_weight_factor:.2f}×{P1s+P2s}/({q_allow}×{L:.2f})",
                     _rnd_up((1 + self_weight_factor) * (P1s + P2s) / (q_allow * L)), "m", P.REF_FOUNDATION_SOIL)
    B = max(B, max(col1["a"], col2["a"]) / 1000 + 0.2)
    q_s = (1 + self_weight_factor) * (P1s + P2s) / (B * L)
    rep.check("جهد التشغيل ≤ q allow", q_s, q_allow, "kN/m²", P.REF_FOUNDATION_SOIL)

    # توزيع خطي للضغط الأقصى (محصلة القصوى ممكن متكونش في المنتصف)
    Pu = Pu1 + Pu2
    xu = Pu2 * spacing / Pu + x1
    eu = xu - L / 2
    rep.step("لامركزية المحصلة القصوى", "eu = xu − L/2", f"{xu:.3f} − {L/2:.3f}", eu, "m")
    q_lo = Pu / (B * L) * (1 - 6 * eu / L)
    q_hi = Pu / (B * L) * (1 + 6 * eu / L)
    rep.step("الضغط الأقصى عند الطرفين", "qu = Pu/(B·L)·(1 ∓ 6eu/L)", "", f"{q_lo:.1f} / {q_hi:.1f}", "kN/m²",
             P.REF_FOUNDATION_SOIL)
    if q_lo < 0:
        rep.note("فيه شد تحت طرف القاعدة: عدّل الطول أو x1.")

    # مخطط القص والعزم (نقاط ـ الأعمدة أحمال مركزة)
    n = 4000
    dx = L / n
    xs = [i * dx for i in range(n + 1)]
    c_pos = [(x1, Pu1), (x1 + spacing, Pu2)]
    V, M = [0.0], [0.0]
    for i in range(1, n + 1):
        x = xs[i]
        q = B * (q_lo + (q_hi - q_lo) * (x - dx / 2) / L)
        v = V[-1] + q * dx
        for xc, Pc in c_pos:
            if xs[i - 1] < xc <= x:
                v -= Pc
        V.append(v)
        M.append(M[-1] + (V[-2] + v) / 2 * dx)
    Mpos = max(M)
    Mneg = -min(M)
    # إشارة: M موجب = شد في الأسفل (ضغط التربة لأعلى)
    rep.step("أقصى عزم (شد سفلي — تحت الأعمدة / الكابولي)", "من مخطط العزوم", "", Mpos, "kN·m")
    rep.step("أقصى عزم (شد علوي — بين العمودين)", "من مخطط العزوم", "", Mneg, "kN·m")

    # السمك
    auto_h = h is None
    h = h or 500.0
    loc1 = "edge" if x1 * 1000 < col1["b"] / 2 + 1 else "interior"
    while True:
        d = h - cover - 20
        ok = _punch(None, "", Pu1, (q_lo + q_hi) / 2, col1["b"], col1["a"], d, fcu, loc1) and \
            _punch(None, "", Pu2, (q_lo + q_hi) / 2, col2["b"], col2["a"], d, fcu, "interior")
        qcu = P.QCU_UNCRACKED * P.sqrt_fcu_gc(fcu)
        Vmax = 0.0
        for xc, c in ((x1, col1), (x1 + spacing, col2)):
            for side in (-1, 1):
                xcrit = xc + side * (c["b"] / 2000 + d / 2000)
                if 0 < xcrit < L:
                    Vmax = max(Vmax, abs(V[min(n, int(xcrit / dx))]))
        ok = ok and Vmax * 1e3 / (B * 1000 * d) <= qcu
        if ok or not auto_h or h > 2500:
            break
        h += 50
    d = h - cover - 20
    rep.step("سمك القاعدة h", "", "أقل سمك يحقق القص الثاقب والقص (خطوات 50 مم)" if auto_h else "مُدخل", float(h), "mm")
    _punch(rep, "العمود 1", Pu1, (q_lo + q_hi) / 2, col1["b"], col1["a"], d, fcu, loc1)
    _punch(rep, "العمود 2", Pu2, (q_lo + q_hi) / 2, col2["b"], col2["a"], d, fcu, "interior")
    qu1w = rep.step("أقصى إجهاد قص في اتجاه واحد (على d/2 من وش العمود)", "q = V/(B·d)",
                    f"{Vmax:.0f}×10³/({B*1000:.0f}×{d:.0f})", Vmax * 1e3 / (B * 1000 * d), "N/mm²", P.REF_QCU_UNC)
    rep.check("q ≤ qcu", qu1w, P.QCU_UNCRACKED * P.sqrt_fcu_gc(fcu), "N/mm²", P.REF_QCU_UNC)

    res = {"B × L × h": f"{B*1000:.0f} × {L*1000:.0f} × {h:.0f} mm", "q_service": round(q_s, 1)}
    rep.step("— التسليح الطولي —", "", "", "", "")
    s = strip_steel(Mpos / B, h, fcu, fy, rep, "(طولي سفلي)", cover)
    res["long_bottom"] = s and s["bars"]
    s = strip_steel(Mneg / B, h, fcu, fy, rep, "(طولي علوي)", cover)
    res["long_top"] = s and s["bars"]
    rep.step("— التسليح العرضي (كمرة عرضية تحت كل عمود) —", "", "", "", "")
    for name, c, Puc in (("1", col1, Pu1), ("2", col2, Pu2)):
        w_strip = rep.step(f"عرض الشريحة العرضية تحت العمود {name}", "b_col + d (ممارسة)", f"{c['b']} + {d:.0f}",
                           c["b"] + d, "mm", P.Ref("ممارسة تصميم — مش بند في الكود", None, False, "عرض الشريحة العرضية افتراض"))
        arm = (B * 1000 - c["a"]) / 2 / 1000
        Mt = rep.step(f"العزم العرضي (العمود {name})", "(Pu/B)·x²/2", f"({Puc:.0f}/{B})×{arm:.3f}²/2", Puc / B * arm ** 2 / 2,
                      "kN·m")
        s = strip_steel(Mt / (w_strip / 1000), h, fcu, fy, rep, f"(عرضي تحت العمود {name}، لكل متر من الشريحة)",
                        cover + 20)
        res[f"transverse_col{name}"] = s and f"{s['bars']} في عرض {w_strip:.0f} mm"
    rep.note("باقي العرض العرضي: تسليح أدنى (ممكن نفس التسليح الأدنى للبلاطات).")
    rep.results = res
    return rep


# ------------------------------------------------------------------ لبشة (طريقة جاسئة)
def design_raft(Lx, Ly, columns, q_allow, fcu=30, fy=400, t=None, cover=75.0, title=None):
    """Lx, Ly أبعاد اللبشة (m)، الأصل في ركن اللبشة.
    columns: list of dict(x=, y=, c1=, c2=, D=, L=) — x,y بالمتر لمحور العمود، c1 في اتجاه x، c2 في اتجاه y (mm).
    q_allow: جهد التربة المسموح (kN/m²) — متقارن بالضغط شامل وزن اللبشة."""
    rep = Report(title or f"لبشة {Lx}×{Ly} م — طريقة جاسئة — ECP 203-2020")
    rep.inputs = {"Lx × Ly": f"{Lx} × {Ly} m", "عدد الأعمدة": len(columns), "q allow": f"{q_allow} kN/m²",
                  "fcu / fy": f"{fcu} / {fy}"}
    rep.note("طريقة جاسئة بتوزيع ضغط خطي: صالحة للبشات الجاسئة نسبياً والأعمدة المنتظمة. للتصميم النهائي حلل اللبشة بـ SAFE "
             "وصمم الشرائح بـ design_slab_strip.")
    A = Lx * Ly
    Ix, Iy = Lx * Ly ** 3 / 12, Ly * Lx ** 3 / 12
    Ps = sum(c["D"] + c["L"] for c in columns)
    Pu = sum(P.LOAD_D * c["D"] + P.LOAD_L * c["L"] for c in columns)
    xr = sum((c["D"] + c["L"]) * c["x"] for c in columns) / Ps
    yr = sum((c["D"] + c["L"]) * c["y"] for c in columns) / Ps
    ex, ey = xr - Lx / 2, yr - Ly / 2
    rep.step("مجموع أحمال التشغيل / القصوى", "", "", f"{Ps:.0f} / {Pu:.0f}", "kN", P.REF_LOADS)
    rep.step("لامركزية المحصلة ex / ey", "e = Σ(P·x)/ΣP − L/2", "", f"{ex:.3f} / {ey:.3f}", "m")

    def q_at(Ptot, x, y):
        return Ptot / A + Ptot * ey * (y - Ly / 2) / Ix + Ptot * ex * (x - Lx / 2) / Iy

    # السمك من القص الثاقب
    auto_t = t is None
    t = t or 600.0
    while True:
        d = t - cover - 25
        ok = True
        for c in columns:
            loc, c1, c2 = _raft_loc(c, Lx, Ly, d)
            Puc = P.LOAD_D * c["D"] + P.LOAD_L * c["L"]
            qu = q_at(Pu, c["x"], c["y"])
            ok = ok and _punch(None, "", Puc, qu, c1, c2, d, fcu, loc)
        if ok or not auto_t or t > 3000:
            break
        t += 50
    rep.step("سمك اللبشة t", "", "أقل سمك يحقق القص الثاقب لكل الأعمدة (خطوات 50 مم)" if auto_t else "مُدخل", float(t), "mm")
    d = t - cover - 25
    W = P.GAMMA_RC * t / 1000 * A
    rep.step("وزن اللبشة", "γ·t·A", f"25×{t/1000}×{A:.1f}", W, "kN", P.REF_UNIT_WEIGHT)
    corners = [(0, 0), (Lx, 0), (0, Ly), (Lx, Ly)]
    qs = [(Ps + W) / A + Ps * ey * (y - Ly / 2) / Ix + Ps * ex * (x - Lx / 2) / Iy for x, y in corners]
    rep.step("ضغط التشغيل عند الأركان (شامل وزن اللبشة)", "q = (P+W)/A ± P·ey·y/Ix ± P·ex·x/Iy", "",
             " / ".join(f"{q:.1f}" for q in qs), "kN/m²", P.REF_FOUNDATION_SOIL)
    rep.check("أقصى ضغط تشغيل ≤ q allow", max(qs), q_allow, "kN/m²", P.REF_FOUNDATION_SOIL)
    rep.check("مفيش شد تحت اللبشة", min(qs), 0.0, "kN/m²", P.REF_FOUNDATION_SOIL, "≥")

    rep.step("— القص الثاقب عند كل عمود —", "", "", "", "")
    for i, c in enumerate(columns, 1):
        loc, c1, c2 = _raft_loc(c, Lx, Ly, d)
        Puc = P.LOAD_D * c["D"] + P.LOAD_L * c["L"]
        _punch(rep, f"C{i} ({c['x']},{c['y']})", Puc, q_at(Pu, c["x"], c["y"]), c1, c2, d, fcu, loc)

    # عزوم تقريبية بطريقة الشرائح
    rep.step("— العزوم (تقريبي: شرائح مستمرة جاسئة) —", "", "", "", "")
    ref_strip = P.Ref("ممارسة: شرائح مستمرة بعزم qu·l²/10", None, False,
                      "تقريب هندسي مش بند في الكود؛ استخدم عزوم SAFE للتصميم النهائي")
    qu_avg = rep.step("متوسط الضغط الأقصى الصافي", "qu = ΣPu/A", f"{Pu:.0f}/{A:.1f}", Pu / A, "kN/m²")
    res = {"t_mm": t, "q_max_service": round(max(qs), 1)}
    for axis, key in (("x", "x"), ("y", "y")):
        coords = sorted({round(c[key], 3) for c in columns})
        spans = [b - a for a, b in zip(coords, coords[1:])] or [Lx if axis == "x" else Ly]
        l = max(spans)
        M = rep.step(f"عزم الشريحة في اتجاه {axis} (أكبر بحر {l:.2f} م)", "M = qu·l²/10", f"{qu_avg:.1f}×{l:.2f}²/10",
                     qu_avg * l ** 2 / 10, "kN·m/m", ref_strip)
        s = strip_steel(M, t, fcu, fy, rep, f"(اتجاه {axis} — علوي في البحور وسفلي تحت الأعمدة)", cover)
        res[f"mesh_{axis}"] = s and s["bars"]
    rep.note("حط الشبكة دي علوي وسفلي في الاتجاهين كحد أدنى، وزوّد تحت الأعمدة حسب عزوم SAFE.")
    rep.results = res
    return rep


def _raft_loc(c, Lx, Ly, d):
    near_x = min(c["x"] * 1000 - c["c1"] / 2, (Lx - c["x"]) * 1000 - c["c1"] / 2) < d
    near_y = min(c["y"] * 1000 - c["c2"] / 2, (Ly - c["y"]) * 1000 - c["c2"] / 2) < d
    if near_x and near_y:
        return "corner", c["c1"], c["c2"]
    if near_x:      # الحافة الحرة موازية لمحور y → القطع في اتجاه x (c1)
        return "edge", c["c1"], c["c2"]
    if near_y:
        return "edge", c["c2"], c["c1"]
    return "interior", c["c1"], c["c2"]
