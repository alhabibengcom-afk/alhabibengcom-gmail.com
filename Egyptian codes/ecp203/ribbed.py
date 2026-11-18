"""البلاطات ذات الأعصاب والقوالب المفرغة (الهوردي) - ECP 203-2020.

الحساب لكل عصب: العصب قطاع T، عرض الشفة = المسافة بين محاور الأعصاب.
القوالب (البلوكات) مش داخلة في المقاومة، لكن وزنها داخل في الأحمال.
"""
from __future__ import annotations

import math

from . import params as P
from .beam import design_flexure
from .report import Report


def _dims_checks(rep, e_clear, bw, h, ts):
    rep.check("المسافة الخالصة بين الأعصاب", e_clear, P.HB_CLEAR_MAX, "mm", P.REF_HB_DIMS)
    rep.check("عرض العصب ≥ max(100 , h/3)", bw, max(P.HB_RIB_MIN, h * P.HB_RIB_DEPTH_FRAC), "mm", P.REF_HB_DIMS, "≥")
    rep.check("سمك بلاطة الضغط ≥ max(50 , e/10)", ts, max(P.HB_TS_MIN, P.HB_TS_FRAC * e_clear), "mm", P.REF_HB_DIMS, "≥")


def _rib_loads(rep, spacing, bw, h, ts, block_weight, finishes, wL):
    """بيرجع (wD, wL) لكل م² شاملة وزن الأعصاب والبلاطة والبلوك."""
    s = spacing / 1000
    conc = (ts / 1000) * s + (bw / 1000) * ((h - ts) / 1000)
    w_self = rep.step("وزن الخرسانة لكل م²", "γ·[ts·s + bw·(h − ts)] / s", f"25×{conc:.4f}/{s}",
                      P.GAMMA_RC * conc / s, "kN/m²", P.REF_UNIT_WEIGHT)
    wD = rep.step("الحمل الميت الكلي wD", "وزن الخرسانة + البلوك + التشطيبات", f"{w_self:.2f} + {block_weight} + {finishes}",
                  w_self + block_weight + finishes, "kN/m²")
    return wD, wL


def _rib_shear(rep, wu_rib, L, bw, d, fcu, factor):
    Qu = factor * wu_rib * L
    qu = rep.step("إجهاد القص في العصب", "qu = Qu/(bw·d)", f"{Qu:.2f}×10³/({bw}×{d:.0f})", Qu * 1e3 / (bw * d), "N/mm²")
    rep.check("qu ≤ qcu (الأعصاب تقاوم القص بالخرسانة فقط)", qu, P.QCU_UNCRACKED * P.sqrt_fcu_gc(fcu), "N/mm²",
              P.REF_HB_SHEAR)
    if qu > P.QCU_UNCRACKED * P.sqrt_fcu_gc(fcu):
        rep.note("القص أكبر من مقاومة الخرسانة: وسّع العصب أو اعمل جزء مصمت (Solid) جنب الركيزة.")


def design_hollow_block_one_way(L, h, ts, bw, block_width, finishes, wL, block_weight=1.0, support="both_ends",
                                fcu=25, fy=400, cover=20.0, title=None):
    """L بحر فعال (m)، h عمق كلي، ts بلاطة الضغط، bw عرض العصب، block_width عرض البلوك (= المسافة الخالصة) — mm.
    finishes و wL و block_weight بالـ kN/m². support: simple | one_end | both_ends."""
    rep = Report(title or f"هوردي اتجاه واحد — بحر {L} م، عمق {h} مم — ECP 203-2020")
    spacing = bw + block_width
    rep.inputs = {"البحر": f"{L} m", "h / ts / bw": f"{h} / {ts} / {bw} mm", "عرض البلوك": f"{block_width} mm",
                  "المسافة بين المحاور": f"{spacing} mm", "تشطيبات / حي / وزن بلوك": f"{finishes} / {wL} / {block_weight} kN/m²",
                  "الارتكاز": support, "fcu / fy": f"{fcu} / {fy}"}
    _dims_checks(rep, block_width, bw, h, ts)
    wD, wL = _rib_loads(rep, spacing, bw, h, ts, block_weight, finishes, wL)
    wu = rep.step("الحمل الأقصى wu", "1.4 D + 1.6 L", f"1.4×{wD:.2f} + 1.6×{wL}", P.LOAD_D * wD + P.LOAD_L * wL,
                  "kN/m²", P.REF_LOADS)
    wr = rep.step("الحمل على العصب الواحد", "wu × s", f"{wu:.2f}×{spacing/1000}", wu * spacing / 1000, "kN/m")
    kp, kn = P.SLAB_K[support]
    Mp = rep.step("العزم الموجب للعصب", f"wr·L²/{kp:.0f}", f"{wr:.2f}×{L}²/{kp:.0f}", wr * L * L / kp, "kN·m",
                  P.REF_SLAB_K)
    res = {"spacing_mm": spacing, "wu_kN_m2": round(wu, 2)}
    rep.step("— تسليح العصب السفلي (قطاع T) —", "", "", "", "")
    r = design_flexure(bw, h, fcu, fy, Mp, cover, 0, flange_width=spacing, flange_t=ts, rep=rep, bar_max=16)
    res["rib_bottom"] = r.get("tension_bars")
    if kn:
        Mn = rep.step("العزم السالب عند الركيزة (للعصب)", f"wr·L²/{kn:.0f}", f"{wr:.2f}×{L}²/{kn:.0f}", wr * L * L / kn,
                      "kN·m", P.REF_SLAB_K)
        rep.step("— التسليح العلوي (الجزء المصمت فوق الركيزة، لكل عصب) —", "", "", "", "")
        r2 = design_flexure(spacing, h, fcu, fy, -Mn, cover, 0, rep=rep, bar_max=16)
        res["top_per_rib"] = r2.get("tension_bars")
        rep.note("فوق الركائز المستمرة البلاطة لازم تكون مصمتة (من غير بلوك) بالعرض اللي يغطي العزم السالب والقص.")
    d = h - cover - 6
    _rib_shear(rep, wr, L, bw, d, fcu, 0.5 if support == "simple" else 0.6)
    # الأعصاب العرضية
    n_cross = 0
    if wL <= 3 and L > 5:
        n_cross = 1
    elif wL > 3 and 4 <= L <= 7:
        n_cross = 1
    elif wL > 3 and L > 7:
        n_cross = 3
    res["cross_ribs"] = n_cross
    rep.step("عدد الأعصاب العرضية", "حمل حي ≤ 3 وبحر > 5 م → 1 ؛ حمل > 3: (4–7 م → 1) ، (> 7 م → 3)",
             f"wL = {wL} ، L = {L}", str(n_cross), "", P.HB_CROSS_RIBS)
    if n_cross:
        rep.note("العصب العرضي بنفس قطاع وتسليح العصب الرئيسي السفلي، وتسليحه العلوي نصف السفلي على الأقل.")
    rep.note("بلاطة الضغط: شبكة توزيع (الكود بيحدد حد أدنى بالـ mm²/m وسيخ بين كل عصبين) — راجع صفحة 249.")
    rep.note("الترخيم مش متحسب: راجع حدود الكود للبلاطات ذات الأعصاب أو احسبه.")
    rep.results = res
    return rep


def design_hollow_block_two_way(a, b, h, ts, bw, block_width, finishes, wL, block_weight=1.0, cont_a=2, cont_b=2,
                                fcu=25, fy=400, cover=20.0, title=None):
    """هوردي في اتجاهين بشفة ضغط كاملة على كمرات جاسئة. a ≤ b (m)."""
    if a > b:
        a, b, cont_a, cont_b = b, a, cont_b, cont_a
    rep = Report(title or f"هوردي اتجاهين {a}×{b} م — ECP 203-2020")
    spacing = bw + block_width
    rep.inputs = {"a × b": f"{a} × {b} m", "h / ts / bw": f"{h} / {ts} / {bw} mm", "المسافة بين المحاور": f"{spacing} mm",
                  "جوانب مستمرة (a / b)": f"{cont_a} / {cont_b}", "تشطيبات / حي": f"{finishes} / {wL} kN/m²"}
    _dims_checks(rep, block_width, bw, h, ts)
    wD, wL = _rib_loads(rep, spacing, bw, h, ts, block_weight, finishes, wL)
    wu = rep.step("الحمل الأقصى wu", "1.4 D + 1.6 L", "", P.LOAD_D * wD + P.LOAD_L * wL, "kN/m²", P.REF_LOADS)
    ma, mb = P.SLAB_M[cont_a], P.SLAB_M[cont_b]
    r = rep.step("نسبة المستطيلية r", "r = (mb·b)/(ma·a)", f"({mb}×{b})/({ma}×{a})", mb * b / (ma * a), "", P.REF_SLAB_M)
    if r > P.TWO_WAY_R_MAX:
        rep.note("r > 2: البلاطة تتصمم اتجاه واحد في البحر القصير.")
        return design_hollow_block_one_way(a, h, ts, bw, block_width, finishes, wL, block_weight,
                                           {0: "simple", 1: "one_end", 2: "both_ends"}[cont_a], fcu, fy, cover)
    alpha = rep.step("نصيب البحر القصير α", "α = r⁴/(1 + r⁴)", f"{r:.3f}⁴/(1 + {r:.3f}⁴)", r ** 4 / (1 + r ** 4), "",
                     P.REF_HB_TWOWAY)
    beta = 1 - alpha
    res = {"r": round(r, 3)}
    for name, coef, span, cont in (("a", alpha, a, cont_a), ("b", beta, b, cont_b)):
        k = {0: "simple", 1: "one_end", 2: "both_ends"}[cont]
        kp, kn = P.SLAB_K[k]
        wr = coef * wu * spacing / 1000
        Mp = rep.step(f"العزم الموجب لعصب الاتجاه {name}", f"coef·wu·s·{name}²/{kp:.0f}", f"{coef:.3f}×{wu:.2f}×{spacing/1000}×{span}²/{kp:.0f}",
                      wr * span ** 2 / kp, "kN·m", P.REF_SLAB_K)
        cov = cover if name == "a" else cover + 12
        rr = design_flexure(bw, h, fcu, fy, Mp, cov, 0, flange_width=spacing, flange_t=ts, rep=rep, bar_max=16)
        res[f"rib_bottom_{name}"] = rr.get("tension_bars")
        if kn:
            Mn = wr * span ** 2 / kn
            rep.step(f"العزم السالب لكل عصب (اتجاه {name})", f"coef·wu·s·{name}²/{kn:.0f}", "", Mn, "kN·m", P.REF_SLAB_K)
            r2 = design_flexure(spacing, h, fcu, fy, -Mn, cover, 0, rep=rep, bar_max=16)
            res[f"top_per_rib_{name}"] = r2.get("tension_bars")
        _rib_shear(rep, wr, span, bw, h - cov - 6, fcu, 0.5 if cont == 0 else 0.6)
    rep.note("فوق الركائز البلاطة مصمتة، ومفيش بلوك فوق الكمرات.")
    rep.results = res
    return rep
