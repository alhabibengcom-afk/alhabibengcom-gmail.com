"""السلالم الخرسانية (Waist slab) - ECP 203-2020.

الكود مفيهوش باب خاص بالسلالم، فالسلم بيتصمم كبلاطة اتجاه واحد بنفس بنود
البلاطات (السمك، التسليح، القص) والأحمال على المسقط الأفقي.

نوعين:
- longitudinal: السلم شايل بين كمرتين/بسطتين في اتجاه الطلوع (بحر = المسقط الأفقي).
- cantilever: درج كابولي طالع من حائط أو كمرة جانبية (بحر = عرض الدرجة).
"""
from __future__ import annotations

import math

from . import params as P
from .report import Report
from .slab import strip_steel


def design_stair(span, riser, going, t, finishes=1.5, wL=3.0, kind="longitudinal", support="simple",
                 width=1.2, fcu=25, fy=400, cover=20.0, title=None):
    """span: المسقط الأفقي للبحر (m) للنوع longitudinal، أو عرض الدرجة (m) للكابولي.
    riser / going / t بالـ mm (t = سمك البلاطة المائلة عمودياً عليها). الأحمال kN/m² على المسقط الأفقي."""
    rep = Report(title or f"سلم ({'طولي' if kind == 'longitudinal' else 'كابولي'}) — بحر {span} م — ECP 203-2020")
    rep.inputs = {"البحر (أفقي)": f"{span} m", "القائمة / النائمة": f"{riser} / {going} mm", "t": f"{t} mm",
                  "تشطيبات / حي": f"{finishes} / {wL} kN/m²", "النوع": kind, "الارتكاز": support,
                  "عرض السلم": f"{width} m"}
    theta = math.atan(riser / going)
    rep.step("زاوية الميل θ", "θ = atan(R/G)", f"atan({riser}/{going})", math.degrees(theta), "°")
    if not (2 * riser + going >= 600 and 2 * riser + going <= 650):
        rep.note(f"2R + G = {2*riser+going} مم برة النطاق المعتاد للراحة (600–650 مم) — ده اشتراط معماري مش إنشائي.")

    if kind == "longitudinal":
        w_slab = rep.step("وزن البلاطة المائلة (مسقط أفقي)", "γ·t/cosθ", f"25×{t/1000}/{math.cos(theta):.3f}",
                          P.GAMMA_RC * t / 1000 / math.cos(theta), "kN/m²", P.REF_UNIT_WEIGHT)
        w_steps = rep.step("وزن الدرج", "γ·R/2", f"25×{riser/1000}/2", P.GAMMA_RC * riser / 1000 / 2, "kN/m²",
                           P.REF_UNIT_WEIGHT)
        wD = rep.step("الحمل الميت wD", "", f"{w_slab:.2f} + {w_steps:.2f} + {finishes}", w_slab + w_steps + finishes,
                      "kN/m²")
        wu = rep.step("الحمل الأقصى wu", "1.4 D + 1.6 L", f"1.4×{wD:.2f} + 1.6×{wL}", P.LOAD_D * wD + P.LOAD_L * wL,
                      "kN/m²", P.REF_LOADS)
        div = P.SLAB_T_MIN_ONEWAY[support]
        L_incl = span / math.cos(theta)
        rep.check(f"t ≥ L/{div:.0f} (L = البحر المائل)", t, L_incl * 1000 / div, "mm", P.REF_SLAB_T_ONEWAY, "≥")
        kp, kn = P.SLAB_K[support]
        M = rep.step("العزم الموجب", f"wu·L²/{kp:.0f}", f"{wu:.2f}×{span}²/{kp:.0f}", wu * span ** 2 / kp, "kN·m/m",
                     P.REF_SLAB_K)
        res = {"wu_kN_m2": round(wu, 2)}
        s = strip_steel(M, t, fcu, fy, rep, "(رئيسي سفلي)", cover)
        res["main_bottom"] = s and s["bars"]
        if kn:
            Mn = rep.step("العزم السالب عند الركيزة المستمرة", f"wu·L²/{kn:.0f}", "", wu * span ** 2 / kn, "kN·m/m",
                          P.REF_SLAB_K)
            s2 = strip_steel(Mn, t, fcu, fy, rep, "(علوي)", cover)
            res["top"] = s2 and s2["bars"]
        else:
            rep.note("حط تسليح علوي عند الأطراف (أشاير) لمقاومة التثبيت الجزئي، وبالأخص عند الكسرة مع البسطة.")
        Qu = wu * span * 0.5
        d = t - cover - 6
        qu = rep.step("إجهاد القص", "qu = Qu/(1000·d)", f"{Qu:.1f}×10³/(1000×{d:.0f})", Qu * 1e3 / (1000 * d), "N/mm²")
        rep.check("qu ≤ qcu", qu, P.QCU_UNCRACKED * P.sqrt_fcu_gc(fcu), "N/mm²", P.REF_QCU_UNC)
        rep.note("عند الكسرة الداخلية (Re-entrant corner) الأسياخ السفلية لازم تتقاطع وتكمل بطول التماسك، متتثنيش مع الكسرة.")
    else:
        # كابولي: الشريحة = درجة واحدة بعرض going، العمق الفعال متوسط سمك الدرجة
        h_avg = t / math.cos(theta) + riser / 2
        rep.step("متوسط سمك الدرجة", "t/cosθ + R/2", f"{t}/{math.cos(theta):.3f} + {riser}/2", h_avg, "mm")
        wD = rep.step("الحمل الميت لكل م² (مسقط)", "γ·h_avg + تشطيبات", f"25×{h_avg/1000:.3f} + {finishes}",
                      P.GAMMA_RC * h_avg / 1000 + finishes, "kN/m²", P.REF_UNIT_WEIGHT)
        wu = rep.step("الحمل الأقصى wu", "1.4 D + 1.6 L", "", P.LOAD_D * wD + P.LOAD_L * wL, "kN/m²", P.REF_LOADS)
        M = rep.step("العزم عند الركيزة لكل متر", "wu·L²/2", f"{wu:.2f}×{span}²/2", wu * span ** 2 / 2, "kN·m/m")
        res = {"wu_kN_m2": round(wu, 2)}
        s = strip_steel(M, t, fcu, fy, rep, "(علوي — كابولي، لكل متر طولي من السلم)", cover)
        res["top_per_m"] = s and s["bars"]
        rep.check("t ≥ L/10 للكابولي", t, span * 1000 / P.SLAB_T_MIN_ONEWAY["cantilever"], "mm", P.REF_SLAB_T_ONEWAY, "≥")
        rep.note("الكمرة أو الحائط الحامل للدرج الكابولي لازم يتصمم على اللي (Torsion) الناتج.")
        rep.note("لكل درجة: سيخ علوي على الأقل في رأس الدرجة، ومسمار توزيع سفلي.")
    rep.note("السلالم مش ليها باب مستقل في ECP 203: اتصممت كبلاطة اتجاه واحد (بنود البلاطات وصفحات 237–240).")
    rep.results = res
    return rep
