"""الحوائط الخرسانية المسلحة الحاملة - ECP 203-2020 (الباب 6، بند الحوائط).

بيصمم شريحة بعرض متر لحمل محوري وعزم خارج مستوى الحائط:
- الطريقة المبسطة (معادلة 6-56) لو المحصلة جوه قلب القطاع.
- وإلا كقطاع عمود (توافق انفعالات) مع العزوم الإضافية للنحافة.
وبيحدد التسليح الرأسي والأفقي (شبكتين).

القص داخل مستوى الحائط والانحناء داخل المستوى (حوائط القص) مش متغطيين هنا:
لحوائط القص استخدم design_column بقطاع (t × L) مع قوى ETABS.
"""
from __future__ import annotations

import math

from . import params as P
from .bars import bar_area
from .column import moment_capacity_at, rect_layers
from .report import Report


def design_wall(t, H, L, fcu, fy, Pu, Mu=0.0, braced=True, end="restrained", cover=25.0, title=None):
    """t سمك (mm)، H الارتفاع الصافي (m)، L طول الحائط (m)،
    Pu حمل أقصى لكل متر طولي (kN/m)، Mu عزم أقصى خارج المستوى (kN·m/m).
    end: restrained (ممنوع من الدوران) | pinned | sway."""
    rep = Report(title or f"حائط خرساني سمك {t} مم، ارتفاع {H} م — ECP 203-2020")
    rep.inputs = {"t": f"{t} mm", "H صافي": f"{H} m", "L": f"{L} m", "fcu / fy": f"{fcu} / {fy}",
                  "Pu": f"{Pu} kN/m", "Mu (خارج المستوى)": f"{Mu} kN·m/m",
                  "المبنى": "مقيد" if braced else "غير مقيد", "الأطراف": end}
    b = 1000.0
    Ac = b * t
    rep.check("طول الحائط > 5 أضعاف السمك", L * 1000, 5 * t, "mm", P.REF_WALL_DEF, "≥")
    rep.check("أقل سمك للحائط", t, P.WALL_MIN_T, "mm", P.REF_WALL_DEF, "≥")
    if L * 1000 < 5 * t:
        rep.note("الطول أقل من 5 أضعاف السمك: صممه كعمود (design_column).")

    k = P.WALL_K[end]
    He = rep.step("الارتفاع الفعال He", "He = k·H", f"{k}×{H*1000:.0f}", k * H * 1000, "mm", P.REF_WALL_SIMPLE)
    lam = rep.step("نسبة النحافة λ", "λ = He / t", f"{He:.0f}/{t}", He / t, "", P.REF_WALL_SHORT)
    rep.check("λ ≤ أقصى نحافة للحوائط", lam, P.WALL_SLENDER_MAX[braced], "", P.REF_WALL_SLENDER)
    short = lam <= P.WALL_SHORT[braced]
    rep.note(f"الحائط {'قصير' if short else 'نحيف'} (λ = {lam:.1f}، الحد {P.WALL_SHORT[braced]:.0f}).")

    emin = max(P.E_MIN_RATIO * t, P.E_MIN_ABS)
    e = abs(Mu) * 1e3 / Pu if Pu else float("inf")
    rep.step("اللامركزية e", "e = Mu / Pu ، emin = max(0.05t , 20)", f"{Mu}/{Pu} ، emin = {emin:.0f}", max(e, emin), "mm",
             P.REF_EMIN)

    t_lim = max(P.WALL_T_MIN_RATIO * min(He, L * 1000), P.WALL_T_ABS)
    simple_ok = max(e, emin) <= t / 6 and t >= t_lim
    res = {}
    if simple_ok:
        rep.step("— الطريقة المبسطة (معادلة 6-56) —", "", "", "", "")
        rep.check("المحصلة داخل قلب القطاع (e ≤ t/6)", max(e, emin), t / 6, "mm", P.REF_WALL_SIMPLE_COND)
        rep.check("t ≥ 0.04·min(He , L) ≥ 100 مم", t, t_lim, "mm", P.REF_WALL_SIMPLE_COND, "≥")
        Pcap = rep.step("مقاومة الحائط Pu,cap", "0.8 × 0.35 fcu·Ac × [1 − (He/32t)²]",
                        f"0.8×0.35×{fcu}×{Ac:.0f}×[1 − ({He:.0f}/(32×{t}))²]",
                        0.8 * P.COL_CONC * fcu * Ac * (1 - (He / (32 * t)) ** 2) / 1e3, "kN/m", P.REF_WALL_SIMPLE)
        rep.check("Pu ≤ Pu,cap", Pu, Pcap, "kN/m", P.REF_WALL_SIMPLE)
        state = "compression"
        As_req = 0.0
    else:
        rep.step("— التصميم كقطاع عمود (شريحة 1 م) —", "", "", "", "")
        Madd = 0.0 if short else Pu * (lam ** 2 * t / P.DELTA_ADD_DIV) / 1e3
        if Madd:
            rep.step("العزم الإضافي للنحافة", "Madd = Pu·λ²·t/2000", f"{Pu}×{lam:.1f}²×{t}/2000", Madd, "kN·m/m",
                     P.REF_ADD_MOM)
        Md = max(abs(Mu) + Madd, Pu * emin / 1e3)
        rep.step("العزم التصميمي", "Md = max(|Mu| + Madd , Pu·emin)", "", Md, "kN·m/m", P.REF_EMIN)
        state = "flexure"
        As_req = None
        for dia in (10, 12, 14, 16, 18, 20):
            for n in range(4, 11):  # أسياخ لكل وجه لكل متر
                if 1000 / n > P.WALL_V_MAX_SPACING:
                    continue
                layers = rect_layers(b, t, cover, 0, n, 0, dia)
                M = moment_capacity_at(b, t, fcu, fy, layers, Pu * 1e3)
                if M and M / 1e6 >= Md:
                    As_req = 2 * n * bar_area(dia)
                    rep.step("مقاومة العزم عند Pu (توافق انفعالات)", "", f"{n}Ø{dia}/m لكل وجه", M / 1e6, "kN·m/m",
                             P.Ref("بند 4-2-1-3 (الحوائط تُصمم كأعمدة)", 297))
                    break
            if As_req:
                break
        if As_req is None:
            rep.check("وجود تسليح يحقق العزم", 1, 0, "", P.REF_WALL_V_DETAIL)
            rep.note("مفيش تسليح معقول يشيل العزم: زوّد السمك.")
            As_req = 0.0

    # التسليح الرأسي
    rep.step("— التسليح الرأسي (شبكتين) —", "", "", "", "")
    mild = 0 if P.is_mild(fy) else 1
    rho_min = P.WALL_V_MIN[state][mild]
    As_min = rep.step("أدنى تسليح رأسي (الوجهين)", f"ρmin = {rho_min*100:.2f}% Ac", f"{rho_min}×{Ac:.0f}",
                      rho_min * Ac, "mm²/m", P.REF_WALL_V_MIN)
    As_v = max(As_min, As_req)
    rep.check("As ≤ 4% Ac", As_v, P.WALL_V_MAX * Ac, "mm²/m", P.REF_WALL_V_DETAIL)
    for dia in (10, 12, 14, 16, 18, 20):
        n = max(4, math.ceil(As_v / 2 / bar_area(dia)))
        if 1000 / n <= P.WALL_V_MAX_SPACING and 1000 / n >= 100:
            break
    res["vertical"] = f"{n}Ø{dia}/m لكل وجه ({2*n*bar_area(dia):.0f} mm²/m)"
    rep.step("التسليح الرأسي المختار", "قطر ≥ 10 مم ، مسافة ≤ 250 مم", f"As ≥ {As_v:.0f}", res["vertical"], "",
             P.REF_WALL_V_DETAIL)
    dia_v = dia
    # الأفقي
    rho_h = P.WALL_H_MIN[mild]
    Ah = rep.step("أدنى تسليح أفقي (الوجهين)", f"ρh = {rho_h*100:.2f}% Ac", f"{rho_h}×{Ac:.0f}", rho_h * Ac,
                  "mm²/m", P.REF_WALL_H)
    s_max = min(P.WALL_H_SPACING[0] * dia_v, P.WALL_H_SPACING[1])
    dmin = max(P.WALL_H_MIN_DIA, dia_v / 4)
    for dia in (8, 10, 12, 14, 16):
        if dia < dmin:
            continue
        n = max(math.ceil(1000 / s_max), math.ceil(Ah / 2 / bar_area(dia)))
        if 1000 / n >= 100:
            break
    res["horizontal"] = f"{n}Ø{dia}/m لكل وجه ({2*n*bar_area(dia):.0f} mm²/m)"
    rep.step("التسليح الأفقي المختار", f"قطر ≥ max(8 , Øv/4) ، مسافة ≤ min(15Øv , 200) = {s_max:.0f}", "",
             res["horizontal"], "", P.REF_WALL_H)
    if 2 * (As_v / 2) / Ac > P.WALL_TIES_RHO or state == "compression":
        rep.note(f"حط كانات ربط بين الشبكتين (4 نقط/م² على الأقل) — {P.REF_WALL_TIES}.")
    rep.note("القص والانحناء داخل مستوى الحائط (حوائط القص) مش متغطيين هنا: استخدم design_column بقطاع t × L بقوى ETABS.")
    rep.results = res
    return rep
