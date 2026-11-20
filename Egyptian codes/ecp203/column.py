"""تصميم ومراجعة الأعمدة المستطيلة ذات الكانات العادية - ECP 203-2020.

يشمل: النحافة والعزوم الإضافية، أقل لامركزية، التصميم المحوري، منحنى التفاعل
بتوافق الانفعالات (عزم في اتجاه واحد)، حدود التسليح، والكانات.
"""
from __future__ import annotations

import math

from . import params as P
from .bars import bar_area, fmt
from .report import Report


# ------------------------------------------------------------------ النحافة
def slenderness(t, He, braced, rep: Report, axis=""):
    lam = rep.step(f"نسبة النحافة λ {axis}", "λ = He / t", f"{He} / {t}", He / t, "", P.REF_SLENDER)
    lim_short = P.SHORT_LIMIT[braced]
    lim_max = P.SLENDER_MAX[braced]
    rep.check(f"λ {axis} ≤ أقصى نحافة مسموحة ({'مقيد' if braced else 'غير مقيد'})", lam, lim_max, "", P.REF_SLENDER)
    if lam <= lim_short:
        rep.note(f"العمود قصير في الاتجاه {axis} (λ = {lam:.1f} ≤ {lim_short:.0f}).")
        return lam, 0.0
    delta = rep.step(f"الترخيم الإضافي δ {axis}", "δ = λ² · t / 2000", f"{lam:.2f}² × {t} / 2000",
                     lam ** 2 * t / P.DELTA_ADD_DIV, "mm", P.REF_ADD_MOM)
    rep.note(f"العمود نحيف في الاتجاه {axis} (λ = {lam:.1f} > {lim_short:.0f}).")
    return lam, delta


# ------------------------------------------------------------------ تصميم محوري
def axial_capacity(Ac, As, fcu, fy):
    """Pu (N) طبقاً لمعادلة 4-12-a."""
    return P.COL_CONC * fcu * (Ac - As) + P.COL_STEEL * fy * As


def required_steel_axial(Ac, fcu, fy, Pu_N):
    return (Pu_N - P.COL_CONC * fcu * Ac) / (P.COL_STEEL * fy - P.COL_CONC * fcu)


# ------------------------------------------------------------------ توافق الانفعالات
def rect_layers(b, t, cover, tie, n_face, n_side, dia):
    """طبقات تسليح متماثلة. n_face أسياخ على كل وجه عمودي على اتجاه العزم (يشمل الأركان)،
    n_side أسياخ إضافية على كل جانب. يرجع [(As, depth_from_compression_face)]."""
    d1 = cover + tie + dia / 2
    a = bar_area(dia)
    layers = [(n_face * a, d1)]
    if n_side > 0:
        step = (t - 2 * d1) / (n_side + 1)
        layers += [(2 * a, d1 + i * step) for i in range(1, n_side + 1)]
    layers.append((n_face * a, t - d1))
    return layers


def section_PM(b, t, fcu, fy, layers, c):
    """(P [N], M [N·mm]) حول منتصف القطاع لعمق محور خمول c."""
    sc = P.STRESS_BLOCK * fcu / P.GAMMA_C
    fd = P.fyd(fy)
    a = min(P.BETA1 * c, t)
    Cc = sc * b * a
    Pn = Cc
    M = Cc * (t / 2 - a / 2)
    for As, y in layers:
        eps = P.EPS_CU * (c - y) / c
        fs = max(min(eps * P.ES, fd), -fd)
        if y < a:
            fs -= sc  # إزاحة الخرسانة
        Pn += As * fs
        M += As * fs * (t / 2 - y)
    return Pn, M


def moment_capacity_at(b, t, fcu, fy, layers, Pu_N):
    """أقصى عزم يتحمله القطاع عند حمل Pu، أو None لو Pu أكبر من المقاومة المحورية."""
    lo, hi = 1.0, 20 * t
    if section_PM(b, t, fcu, fy, layers, hi)[0] < Pu_N:
        return None
    for _ in range(200):
        mid = (lo + hi) / 2
        if section_PM(b, t, fcu, fy, layers, mid)[0] < Pu_N:
            lo = mid
        else:
            hi = mid
    return section_PM(b, t, fcu, fy, layers, (lo + hi) / 2)[1]


def interaction_curve(b, t, fcu, fy, layers, n=40):
    pts = []
    for i in range(1, n + 1):
        c = t * 3 * i / n
        Pn, M = section_PM(b, t, fcu, fy, layers, c)
        pts.append((Pn / 1e3, M / 1e6))
    return pts


def _bending_ok(b, t, fcu, fy, cover, tie, n_face, n_side, dia, Pu_N, Mdx, Mdy, biaxial):
    lx = rect_layers(b, t, cover, tie, n_face, n_side, dia)
    ly = rect_layers(t, b, cover, tie, n_side + 2, n_face - 2, dia)
    mx = moment_capacity_at(b, t, fcu, fy, lx, Pu_N)
    my = moment_capacity_at(t, b, fcu, fy, ly, Pu_N)
    if not mx or not my or mx <= 0 or my <= 0:
        return False
    if biaxial:
        return Mdx * 1e6 / mx + Mdy * 1e6 / my <= 1.0
    return mx >= Mdx * 1e6 and my >= Mdy * 1e6


# ------------------------------------------------------------------ الواجهة الرئيسية
def design_column(b, t, fcu, fy, Pu, Mx=0.0, My=0.0, Hex=None, Hey=None, braced=True,
                  location="interior", cover=25.0, tie_dia=8, bar_dia=None, title=None):
    """b,t بالمم (t في اتجاه Mx)، Pu بالـ kN، Mx,My بالـ kN·m، He بالمم."""
    rep = Report(title or f"تصميم عمود {b}×{t} مم — ECP 203-2020")
    rep.inputs = {"b × t": f"{b} × {t} mm", "fcu": f"{fcu} N/mm²", "fy": f"{fy} N/mm²",
                  "Pu": f"{Pu} kN", "Mx (حول المحور الموازي لـ b)": f"{Mx} kN·m", "My": f"{My} kN·m",
                  "He (t / b)": f"{Hex} / {Hey} mm", "المبنى": "مقيد" if braced else "غير مقيد",
                  "موقع العمود": location}
    Ac = b * t
    Pu_N = Pu * 1e3

    rep.check("أقل بعد للعمود", min(b, t), P.COL_MIN_DIM, "mm", P.REF_COL_DETAIL, "≥")
    if fy > P.COL_FY_MAX:
        rep.note(f"fy = {fy} أكبر من الحد الأقصى المسموح للتسليح الطولي في معادلات الأعمدة ({P.REF_COL_FY}).")

    # النحافة
    Madd_x = Madd_y = 0.0
    if Hex:
        _, dx = slenderness(t, Hex, braced, rep, "(اتجاه t)")
        Madd_x = Pu * dx / 1e3
    if Hey:
        _, dy = slenderness(b, Hey, braced, rep, "(اتجاه b)")
        Madd_y = Pu * dy / 1e3
    if Madd_x:
        rep.step("العزم الإضافي Madd,x", "Madd = Pu · δ", f"{Pu} × δ", Madd_x, "kN·m", P.REF_ADD_MOM)
    if Madd_y:
        rep.step("العزم الإضافي Madd,y", "Madd = Pu · δ", f"{Pu} × δ", Madd_y, "kN·m", P.REF_ADD_MOM)

    # أقل لامركزية
    emin_x = max(P.E_MIN_RATIO * t, P.E_MIN_ABS)
    emin_y = max(P.E_MIN_RATIO * b, P.E_MIN_ABS)
    Mmin_x = Pu * emin_x / 1e3
    Mmin_y = Pu * emin_y / 1e3
    Mdx = max(abs(Mx) + Madd_x, Mmin_x)
    Mdy = max(abs(My) + Madd_y, Mmin_y)
    rep.step("أقل لامركزية emin (اتجاه t)", "emin = max(0.05 t , 20 mm)", f"max(0.05×{t} , 20)", emin_x, "mm", P.REF_EMIN)
    rep.step("العزم التصميمي Mx", "Mx,d = max(|Mx| + Madd , Pu·emin)", f"max({abs(Mx)} + {Madd_x:.1f} , {Mmin_x:.1f})",
             Mdx, "kN·m", P.REF_EMIN)
    rep.step("العزم التصميمي My", "My,d = max(|My| + Madd , Pu·emin)", f"max({abs(My)} + {Madd_y:.1f} , {Mmin_y:.1f})",
             Mdy, "kN·m", P.REF_EMIN)

    # حدود التسليح
    mu_max = P.COL_MAX[location]
    small_moment = (abs(Mx) + Madd_x) <= Mmin_x * 1.0001 and (abs(My) + Madd_y) <= Mmin_y * 1.0001

    biaxial = (abs(My) + Madd_y) > Mmin_y and (abs(Mx) + Madd_x) > Mmin_x
    if small_moment:
        rep.note("العزوم أقل من عزوم أقل لامركزية: يُصمم العمود بمعادلة 4-12-a (المحوري المكافئ).")
        As_req = rep.step("التسليح المطلوب (محوري)", "As = (Pu − 0.35fcu·Ac) / (0.67fy − 0.35fcu)",
                          f"({Pu_N:.0f} − 0.35×{fcu}×{Ac}) / (0.67×{fy} − 0.35×{fcu})",
                          required_steel_axial(Ac, fcu, fy, Pu_N), "mm²", P.REF_COL_AXIAL)
        Ac_req = max((Pu_N - P.COL_STEEL * fy * max(As_req, 0)) / (P.COL_CONC * fcu), 0) + max(As_req, 0)
    else:
        As_req = None
        Ac_req = Ac

    As_min = max(P.COL_MIN_REQ * Ac_req, P.COL_MIN_ACT * Ac)
    rep.step("الحد الأدنى للتسليح الطولي", "As,min = max(0.8% Ac,req , 0.6% Ac)",
             f"max(0.008×{Ac_req:.0f} , 0.006×{Ac})", As_min, "mm²", P.REF_COL_MIN)
    As_max = mu_max * Ac
    rep.step("الحد الأقصى للتسليح الطولي", f"As,max = {mu_max*100:.0f}% Ac", f"{mu_max}×{Ac}", As_max, "mm²",
             P.REF_COL_MAX)

    # اختيار الأسياخ والتحقق
    dias = [bar_dia] if bar_dia else [16, 18, 20, 22, 25]
    chosen = None
    for dia in dias:
        for n_face in range(2, 9):
            spacing_ok = (b - 2 * (cover + tie_dia) - dia) / (n_face - 1) <= 250
            for n_side in range(0, 9):
                side_sp = (t - 2 * (cover + tie_dia) - dia) / (n_side + 1)
                if side_sp > 250 or not spacing_ok:
                    continue
                n_total = 2 * n_face + 2 * n_side
                As = n_total * bar_area(dia)
                if As < As_min or As > As_max or axial_capacity(Ac, As, fcu, fy) < Pu_N:
                    continue
                if As_req is not None:
                    ok = As >= As_req
                else:
                    ok = _bending_ok(b, t, fcu, fy, cover, tie_dia, n_face, n_side, dia, Pu_N,
                                     Mdx, Mdy, biaxial)
                if ok and (chosen is None or As < chosen[0]):
                    chosen = (As, dia, n_face, n_side)
            if chosen and chosen[1] == dia:
                break
        if chosen:
            break

    if chosen is None:
        rep.check("وجود تسليح يحقق الأحمال في حدود As,max", 1, 0, "", P.REF_COL_MAX)
        rep.note("مفيش تسليح في الحدود المسموحة يشيل الأحمال: كبّر القطاع أو رتبة الخرسانة.")
        return rep

    As, dia, n_face, n_side = chosen
    n_total = 2 * n_face + 2 * n_side
    rep.step("التسليح المختار", "", f"{n_face} على كل وجه b ، {n_side} إضافي على كل وجه t",
             f"{fmt(n_total, dia)} = {As:.0f}", "mm²")
    rep.check("As ≥ As,min", As, As_min, "mm²", P.REF_COL_MIN, "≥")
    rep.check("As ≤ As,max", As, As_max, "mm²", P.REF_COL_MAX)
    rep.check("قطر السيخ الطولي ≥ 12 مم", dia, P.COL_MIN_BAR, "mm", P.REF_COL_DETAIL, "≥")

    Pmax = axial_capacity(Ac, As, fcu, fy) / 1e3
    rep.step("المقاومة المحورية Pu,max (معادلة 4-12-a)", "0.35fcu(Ac − As) + 0.67fy·As",
             f"0.35×{fcu}×({Ac} − {As:.0f}) + 0.67×{fy}×{As:.0f}", Pmax, "kN", P.REF_COL_AXIAL)
    rep.check("Pu ≤ Pu,max", Pu, Pmax, "kN", P.REF_COL_AXIAL)

    if As_req is None:
        lx = rect_layers(b, t, cover, tie_dia, n_face, n_side, dia)
        ly = rect_layers(t, b, cover, tie_dia, n_side + 2, n_face - 2, dia)
        mx = moment_capacity_at(b, t, fcu, fy, lx, Pu_N) / 1e6
        my = moment_capacity_at(t, b, fcu, fy, ly, Pu_N) / 1e6
        ref_sc = P.Ref("بند 4-2-1-1 و 4-2-1-3-أ (توافق الانفعالات)", 90)
        rep.step("مقاومة العزم Mux عند Pu (توافق انفعالات)", "", "", mx, "kN·m", ref_sc)
        rep.step("مقاومة العزم Muy عند Pu (توافق انفعالات)", "", "", my, "kN·m", ref_sc)
        if biaxial:
            ratio = Mdx / mx + Mdy / my
            rep.check("عزوم مزدوجة: Mx/Mux + My/Muy (خطي متحفظ)", ratio, 1.0, "",
                      P.Ref("بند 6-4-5 معادلة 6-47", 292, False,
                            "تم استخدام تفاعل خطي متحفظ (α=1) بدل جدول αn غير المقروء"))
        else:
            rep.check("Mx,d ≤ Mux", Mdx, mx, "kN·m", ref_sc)
            rep.check("My,d ≤ Muy", Mdy, my, "kN·m", ref_sc)

    # الكانات
    tie = max(P.COL_TIE_MIN_DIA, dia / 4)
    tie = next(d for d in (8, 10, 12) if d >= tie)
    s_tie = min(P.COL_TIE_SPACING_DIA * dia, P.COL_TIE_SPACING_MAX, min(b, t))
    s_tie = math.floor(s_tie / 25) * 25
    rep.step("الكانات", "Ø ≥ max(8 , Ø/4) ، s ≤ min(15Ø , 200 , أقل بعد)",
             f"Ø ≥ max(8 , {dia}/4) ، s ≤ min({15*dia} , 200 , {min(b,t)})",
             f"Ø{tie} @ {s_tie:.0f}", "mm", P.REF_COL_DETAIL)

    rep.results = {"longitudinal": f"{fmt(n_total, dia)} ({As:.0f} mm², {As/Ac*100:.2f}%)",
                   "layout": f"{n_face} أسياخ على كل وجه طوله b ، و{n_side} إضافي على كل وجه طوله t",
                   "ties": f"Ø{tie} @ {s_tie:.0f} mm", "Mx_design_kNm": round(Mdx, 1),
                   "My_design_kNm": round(Mdy, 1), "Pu_max_kN": round(Pmax, 0)}
    return rep
