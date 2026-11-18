"""تصميم ومراجعة الكمرات طبقاً لـ ECP 203-2020 (الانحناء والقص).

المدخلات: الأبعاد بالمم، fcu و fy بالـ N/mm²، العزوم بالـ kN·m، القص بالـ kN.
"""
from __future__ import annotations

import math

from . import params as P
from .bars import bar_area, choose_bars, fmt
from .report import Report


# ------------------------------------------------------------------ مساعدات
def cmax_over_d(fy: float) -> float:
    eps_y = P.fyd(fy) / P.ES
    cb = P.EPS_CU / (P.EPS_CU + eps_y)
    return P.CMAX_FACTOR * cb


def dprime_limit(fy: float) -> float:
    keys = sorted(P.DPRIME_LIMIT)
    k = min(keys, key=lambda x: abs(x - fy))
    return P.DPRIME_LIMIT[k]


def min_flexural_steel(fcu, fy, b, d, as_req, rep: Report | None = None):
    """الحد الأدنى للتسليح - بند 4-2-1-2-ح."""
    rho1 = max(P.MIN_RHO_EQ_A * math.sqrt(fcu) / fy, P.MIN_RHO_EQ_B / fy)
    as1 = rho1 * b * d
    rho_abs = P.MIN_RHO_ABS_MILD if P.is_mild(fy) else P.MIN_RHO_ABS_HT
    as_abs = rho_abs * b * d
    as_min = max(min(as1, P.MIN_INCREASE * as_req), as_abs)
    if rep:
        rep.step("الحد الأدنى لنسبة التسليح μmin",
                 "μmin = max(0.225√fcu/fy , 1.1/fy)",
                 f"max(0.225×√{fcu}/{fy} , 1.1/{fy})", rho1, "", P.REF_MIN_FLEX)
        rep.step("الحد الأدنى للتسليح As,min",
                 "As,min = max( min(μmin·b·d , 1.3·As,req) , ρabs·b·d )",
                 f"max( min({as1:.0f} , 1.3×{as_req:.0f}) , {rho_abs}×{b}×{d} )",
                 as_min, "mm²", P.REF_MIN_ABS)
    return as_min


# ------------------------------------------------------------------ الانحناء
def design_flexure(b, h, fcu, fy, Mu, cover=25.0, stirrup=8.0, d=None, d_comp=None,
                   flange_width=None, flange_t=None, rep: Report | None = None,
                   bar_max=25):
    """تصميم قطاع مستطيل أو T (الشفة في الضغط) لعزم Mu (kN·m)."""
    rep = rep or Report("تصميم الانحناء")
    if d is None:
        d = rep.step("العمق الفعال d (تقريبي: صف واحد Ø20)", "d = h − cover − Øst − Ø/2",
                     f"{h} − {cover} − {stirrup} − 10", h - cover - stirrup - 10, "mm")
    d_comp = d_comp if d_comp is not None else cover + stirrup + 8
    Mu_N = abs(Mu) * 1e6
    fd = P.fyd(fy)
    sc = P.STRESS_BLOCK * fcu / P.GAMMA_C
    rep.step("إجهاد الضغط في المستطيل المكافئ", "0.67 fcu / γc", f"0.67×{fcu}/{P.GAMMA_C}",
             sc, "N/mm²", P.REF_BLOCK)
    rep.step("إجهاد الخضوع التصميمي", "fy / γs", f"{fy}/{P.GAMMA_S}", fd, "N/mm²", P.REF_GAMMA)

    bw = b
    is_T = flange_width is not None and flange_t is not None and Mu >= 0
    b_eff = flange_width if is_T else b

    k = sc * b_eff
    disc = d * d - 2 * Mu_N / k
    cmax = cmax_over_d(fy) * d
    amax = P.BETA1 * cmax
    rep.step("أقصى عمق لمحور الخمول cmax", "cmax = 2/3 · d · εcu/(εcu + fy/(γs·Es))",
             f"2/3 × {d} × 0.003/(0.003 + {fd:.1f}/{P.ES:.0f})", cmax, "mm", P.REF_CMAX)

    As_c = 0.0
    if disc >= 0:
        a = d - math.sqrt(disc)
    else:
        a = float("inf")

    if a <= amax and (not is_T or a <= flange_t):
        a_used = max(a, P.A_MIN_OVER_D * d)
        rep.step("عمق المستطيل المكافئ a", "Mu = 0.67fcu/γc · b · a (d − a/2)  →  a = d − √(d² − 2Mu/(0.67fcu/γc·b))",
                 f"{d} − √({d}² − 2×{Mu_N:.3e}/({sc:.2f}×{b_eff}))", a, "mm", P.REF_BLOCK)
        if a_used != a:
            rep.note(f"a/d = {a/d:.3f} أقل من 0.1، اتاخد a = 0.1d = {a_used:.1f} مم.")
        lever = min(d - a_used / 2, P.LEVER_MAX * d)
        As = rep.step("مساحة تسليح الشد As", "As = Mu / (fy/γs · (d − a/2)) ، (d − a/2) ≤ 0.95d",
                      f"{Mu_N:.3e} / ({fd:.1f} × {lever:.1f})", Mu_N / (fd * lever), "mm²", P.REF_A_MIN)
    elif is_T and a > flange_t and disc >= 0 and a <= amax:
        lever = d - flange_t / 2
        As = rep.step("قطاع T والمحور خارج الشفة: إهمال ضغط الجذع", "As = Mu / (fy/γs · (d − ts/2))",
                      f"{Mu_N:.3e}/({fd:.1f}×{lever:.1f})", Mu_N / (fd * lever), "mm²",
                      P.Ref("بند 4-2-1-2-ه معادلة 4-8", 88))
        Cf = sc * flange_width * flange_t
        rep.check("قوة الشد ≤ مقاومة الشفة للضغط", As * fd / 1e3, Cf / 1e3, "kN",
                  P.Ref("بند 4-2-1-2-ه", 88))
        rep.note("القطاع T بمحور خمول داخل الجذع: الحل التقريبي متحفظ؛ للدقة استخدم توافق الانفعالات.")
    else:
        # تسليح مزدوج
        Mumax = sc * b_eff * amax * (d - amax / 2)
        rep.step("أقصى عزم لقطاع مسلح شد فقط Mu,max", "Mu,max = 0.67fcu/γc · b · amax (d − amax/2)",
                 f"{sc:.2f}×{b_eff}×{amax:.1f}×({d} − {amax/2:.1f})", Mumax / 1e6, "kN·m", P.REF_CMAX)
        As1 = sc * b_eff * amax / fd
        dM = Mu_N - Mumax
        As_c = rep.step("تسليح الضغط As'", "As' = (Mu − Mu,max) / (fy/γs · (d − d'))",
                        f"({Mu_N:.3e} − {Mumax:.3e})/({fd:.1f}×({d} − {d_comp}))",
                        dM / (fd * (d - d_comp)), "mm²", P.Ref("بند 4-2-1-2-د معادلة 4-6 و 4-7", 87))
        As = rep.step("تسليح الشد As", "As = As,max + As'", f"{As1:.0f} + {As_c:.0f}", As1 + As_c, "mm²",
                      P.Ref("بند 4-2-1-2-د معادلة 4-7", 88))
        lim = dprime_limit(fy)
        rep.check("d'/d لضمان خضوع صلب الضغط", d_comp / d, lim, "", P.REF_DPRIME)

    As_min = min_flexural_steel(fcu, fy, bw, d, As, rep)
    As_design = max(As, As_min)
    if As_min > As:
        rep.note("الحد الأدنى للتسليح هو الحاكم.")
    if Mu >= 0 or As_c > 0:
        As_c = max(As_c, P.COMP_STEEL_MIN_RATIO * As_design)
        rep.step("أقل تسليح ضغط في الكمرات (للترخيم طويل المدى)", "As' ≥ 0.10 As",
                 f"0.10 × {As_design:.0f}", P.COMP_STEEL_MIN_RATIO * As_design, "mm²", P.REF_COMP_MIN)

    sel = choose_bars(As_design, bw, cover, stirrup, max_dia=bar_max)
    selc = choose_bars(As_c, bw, cover, stirrup, min_dia=10, max_dia=bar_max) if As_c > 0 else None
    res = {"d_mm": d, "As_req_mm2": round(As, 1), "As_min_mm2": round(As_min, 1),
           "As_design_mm2": round(As_design, 1), "As_comp_mm2": round(As_c, 1)}
    if sel:
        n, dia, area, layers = sel
        res["tension_bars"] = f"{fmt(n, dia)} ({area:.0f} mm², {layers} صف)"
        if layers > 1:
            rep.note("التسليح في صفين: راجع d الفعلي (أقل من المفترض).")
    else:
        rep.note("مفيش ترتيب أسياخ مناسب في العرض ده؛ كبّر القطاع أو استخدم أسياخ مجمعة.")
    if selc:
        res["compression_bars"] = f"{fmt(selc[0], selc[1])} ({selc[2]:.0f} mm²)"
    rep.results.update(res)
    return res


def flexural_capacity(b, d, fcu, fy, As, As_c=0.0, d_comp=50.0):
    """المقاومة القصوى Mu (kN·m) لقطاع مستطيل معلوم التسليح (توافق انفعالات بسيط)."""
    sc = P.STRESS_BLOCK * fcu / P.GAMMA_C
    fd = P.fyd(fy)

    def force(c):
        a = P.BETA1 * c
        eps_c = P.EPS_CU * (c - d_comp) / c
        fs_c = max(min(eps_c * P.ES, fd), -fd)
        eps_t = P.EPS_CU * (d - c) / c
        fs_t = min(eps_t * P.ES, fd)
        return sc * b * a + As_c * (fs_c - (sc if c * P.BETA1 > d_comp else 0)) - As * fs_t, a, fs_c, fs_t

    lo, hi = 1e-3, d
    for _ in range(200):
        mid = (lo + hi) / 2
        if force(mid)[0] > 0:
            hi = mid
        else:
            lo = mid
    c = (lo + hi) / 2
    _, a, fs_c, fs_t = force(c)
    Cc = sc * b * a
    Cs = As_c * (fs_c - (sc if a > d_comp else 0))
    M = Cc * (d - a / 2) + Cs * (d - d_comp)
    return M / 1e6, c


# ------------------------------------------------------------------ القص
def design_shear(b, d, fcu, fy_st, Qu, legs=2, stirrup_dia=8, Pu_comp=0.0, h=None,
                 rep: Report | None = None):
    """تصميم الكانات لقوة قص Qu (kN) عند القطاع الحرج."""
    rep = rep or Report("تصميم القص")
    s = P.sqrt_fcu_gc(fcu)
    qu = rep.step("إجهاد القص الاعتباري qu", "qu = Qu / (b·d)", f"{Qu}×10³ / ({b}×{d})",
                  Qu * 1e3 / (b * d), "N/mm²", P.Ref("بند 4-2-2-1-2-أ معادلة 4-24", 97))
    qmax = min(P.QU_MAX * s, P.QU_MAX_CAP)
    rep.step("أقصى إجهاد قص مسموح qu,max", "qu,max = 0.70√(fcu/γc) ≤ 4.4", f"0.70×√({fcu}/1.5)",
             qmax, "N/mm²", P.REF_QUMAX)
    rep.check("qu ≤ qu,max (أبعاد القطاع كافية)", qu, qmax, "N/mm²", P.REF_QUMAX)

    delta = 1.0
    if Pu_comp > 0 and h:
        delta = min(1 + P.DELTA_COMP * Pu_comp * 1e3 / (b * h), P.DELTA_COMP_MAX)
        rep.step("معامل زيادة مقاومة القص لقوة الضغط δ", "δ = 1 + 0.07·Pu/Ac ≤ 1.5",
                 f"1 + 0.07×{Pu_comp*1e3/(b*h):.2f}", delta, "", P.REF_DELTA)

    qcu_unc = rep.step("مقاومة الخرسانة قبل التشرخ qcu", "qcu = 0.16√(fcu/γc)·δ",
                       f"0.16×√({fcu}/1.5)×{delta:.2f}", P.QCU_UNCRACKED * s * delta, "N/mm²", P.REF_QCU_UNC)
    fd = P.fyd(fy_st)
    mu_min = max(P.STIRRUP_MIN_NUM / fy_st, P.STIRRUP_MIN_MILD if P.is_mild(fy_st) else P.STIRRUP_MIN_HT)
    cracked = qu > qcu_unc
    if not cracked:
        rep.note("qu ≤ qcu: الخرسانة تقاوم القص لوحدها، ويُوضع الحد الأدنى للكانات.")
    else:
        qcu_cr = rep.step("مقاومة الخرسانة بعد التشرخ qcu,cr", "qcu,cr = 0.12√(fcu/γc)·δ",
                          f"0.12×√({fcu}/1.5)×{delta:.2f}", P.QCU_CRACKED * s * delta, "N/mm²", P.REF_QCU_CR)
        qsu = rep.step("الإجهاد المطلوب من الكانات qsu", "qsu = qu − qcu,cr", f"{qu:.3f} − {qcu_cr:.3f}",
                       qu - qcu_cr, "N/mm²", P.REF_QCU_CR)
    # تكبير قطر الكانة تلقائياً لو التباعد أقل من 100 مم
    for dia in [d_ for d_ in (8, 10, 12) if d_ >= stirrup_dia] or [stirrup_dia]:
        Av = legs * bar_area(dia)
        s_min_req = Av / (mu_min * b)
        s_req = Av * fd / (qsu * b) if cracked else float("inf")
        s_use = math.floor(min(s_req, s_min_req, P.STIRRUP_SMAX) / 25) * 25
        if s_use >= 100:
            break
    stirrup_dia = dia
    rep.step(f"التباعد طبقاً للحد الأدنى للكانات (Ø{dia})", "s = Av / (μmin · b) ، μmin = max(0.4/fy , ρ)",
             f"{Av:.0f} / ({mu_min:.5f}×{b})", s_min_req, "mm", P.REF_STIRRUP_MIN)
    if cracked:
        rep.step(f"التباعد المطلوب للكانات (Ø{dia})", "s = Av·(fy/γs) / (qsu·b)",
                 f"{Av:.0f}×{fd:.1f}/({qsu:.3f}×{b})", s_req, "mm", P.Ref("بند 4-2-2-1-5-أ معادلة 4-34", 101))
    rep.step("التباعد المختار (مقرب لأقل 25 مم)", "s = min(s_req , s_min , smax)", "", float(s_use), "mm",
             P.REF_STIRRUP_SMAX)
    if s_use < 100:
        rep.note("التباعد أقل من 100 مم حتى مع Ø12: زوّد عدد الفروع أو كبّر القطاع.")
    if b >= P.FOUR_LEGS_WIDTH and legs < 4:
        rep.note(f"عرض الكمرة ≥ {P.FOUR_LEGS_WIDTH:.0f} مم: الكود يشترط كانات 4 فروع ({P.REF_FOUR_LEGS}).")
    res = {"qu_N_mm2": round(qu, 3), "stirrups": f"{legs} فرع Ø{stirrup_dia} @ {s_use:.0f} mm",
           "stirrups_per_m": round(1000 / s_use, 1) if s_use else None}
    rep.results.update(res)
    return res


# ------------------------------------------------------------------ واجهة موحدة
def design_beam(b, h, fcu, fy, Mu_pos=0.0, Mu_neg=0.0, Qu=0.0, fy_st=240, cover=25.0,
                stirrup_dia=8, legs=2, flange_width=None, flange_t=None, title=None):
    rep = Report(title or f"تصميم كمرة {b}×{h} مم — ECP 203-2020")
    rep.inputs = {"b × h": f"{b} × {h} mm", "fcu": f"{fcu} N/mm²", "fy (رئيسي)": f"{fy} N/mm²",
                  "fy (كانات)": f"{fy_st} N/mm²", "Mu+": f"{Mu_pos} kN·m", "Mu−": f"{Mu_neg} kN·m",
                  "Qu": f"{Qu} kN", "الغطاء": f"{cover} mm"}
    if flange_width:
        rep.inputs["الشفة B × ts"] = f"{flange_width} × {flange_t} mm"
    d = h - cover - stirrup_dia - 10
    out = {}
    if Mu_pos:
        rep.step("— العزم الموجب —", "", "", "", "")
        out["positive"] = design_flexure(b, h, fcu, fy, Mu_pos, cover, stirrup_dia, d=d,
                                         flange_width=flange_width, flange_t=flange_t, rep=rep)
    if Mu_neg:
        rep.step("— العزم السالب (الشفة في الشد → قطاع مستطيل) —", "", "", "", "")
        out["negative"] = design_flexure(b, h, fcu, fy, -abs(Mu_neg), cover, stirrup_dia, d=d, rep=rep)
    if Qu:
        rep.step("— القص —", "", "", "", "")
        out["shear"] = design_shear(b, d, fcu, fy_st, Qu, legs, stirrup_dia, rep=rep)
    rep.results.clear()
    for k, v in out.items():
        for kk, vv in v.items():
            rep.results[f"{k}.{kk}"] = vv
    return rep
