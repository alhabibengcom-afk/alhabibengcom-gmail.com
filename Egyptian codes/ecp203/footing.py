"""تصميم القواعد المنفصلة المسلحة تحت عمود مستطيل - ECP 203-2020.

يشمل: المساحة من جهد التربة المسموح، الضغط الأقصى، القص الثاقب، القص في
اتجاه واحد، العزوم والتسليح، وطول التماسك.

⚠️ جهد التربة المسموح ومعامل وزن القاعدة والردم مدخلات من تقرير التربة /
كود الأساسات 202 (غير موجود في المرجع).
"""
from __future__ import annotations

import math

from . import params as P
from .bars import bar_area
from .beam import min_flexural_steel
from .report import Report


def punching_strength(fcu, d, bo, a_col, b_col, location="interior"):
    s = P.sqrt_fcu_gc(fcu)
    alpha = P.PUNCH_ALPHA[location]
    short, long_ = sorted((a_col, b_col))
    q1 = P.PUNCH_A * (alpha * d / bo + P.PUNCH_A0) * s
    q2 = P.PUNCH_B * (0.5 + short / long_) * s
    q3 = P.PUNCH_C * s
    return min(q1, q2, q3, P.PUNCH_CAP), (q1, q2, q3)


def development_length(fy, fcu, dia, alpha=1.0, eta=1.0):
    fbu = P.FBU * P.sqrt_fcu_gc(fcu)
    Ld = alpha * P.BETA_DEFORMED * eta * P.fyd(fy) * dia / (4 * fbu)
    return max(Ld, P.LD_MIN_DIA * dia, P.LD_MIN_ABS), fbu


def design_isolated_footing(col_a, col_b, D, L, q_allow, fcu=25, fy=400, Mx_s=0.0, My_s=0.0,
                            B=None, Lf=None, h=None, cover=75.0, self_weight_factor=0.10,
                            location="interior", title=None):
    """col_a × col_b: أبعاد العمود (مم)، col_b في اتجاه طول القاعدة Lf.
    D, L: أحمال التشغيل (kN). q_allow: جهد التربة الصافي المسموح (kN/m²).
    Mx_s, My_s: عزوم تشغيل اختيارية (kN·m) حول المحورين (في اتجاه Lf و B).
    """
    rep = Report(title or f"تصميم قاعدة منفصلة تحت عمود {col_a}×{col_b} مم — ECP 203-2020")
    rep.inputs = {"العمود": f"{col_a} × {col_b} mm", "D / L (تشغيل)": f"{D} / {L} kN",
                  "q allow (صافي)": f"{q_allow} kN/m²", "fcu / fy": f"{fcu} / {fy} N/mm²",
                  "Mx / My (تشغيل)": f"{Mx_s} / {My_s} kN·m", "الغطاء": f"{cover} mm",
                  "وزن القاعدة والردم": f"{self_weight_factor*100:.0f}% من الحمل"}

    Ps = D + L
    Pu = rep.step("الحمل الأقصى للعمود Pu", "Pu = 1.4 D + 1.6 L", f"1.4×{D} + 1.6×{L}",
                  P.LOAD_D * D + P.LOAD_L * L, "kN", P.REF_LOADS)

    # -------- الأبعاد
    if B is None or Lf is None:
        A_req = rep.step("المساحة المطلوبة", "A = (1 + k)·Ps / q_allow", f"{1+self_weight_factor:.2f}×{Ps}/{q_allow}",
                         (1 + self_weight_factor) * Ps / q_allow, "m²")
        # نفس البروز في الاتجاهين
        a, b = col_a / 1000, col_b / 1000
        x = (-(a + b) + math.sqrt((a + b) ** 2 - 4 * (a * b - A_req))) / 4
        B = math.ceil((a + 2 * x) * 20) / 20 * 1000
        Lf = math.ceil((b + 2 * x) * 20) / 20 * 1000
        rep.step("أبعاد القاعدة (بروز متساوي، مقرب لأعلى 50 مم)", "B = a + 2x ، L = b + 2x", "",
                 f"{B:.0f} × {Lf:.0f}", "mm")
        rep.note("القاعدة بنفس البروز في الاتجاهين، فالعزوم متساوية تقريباً عند وش العمود.")
    Bm, Lm = B / 1000, Lf / 1000
    A = Bm * Lm

    q_s = (1 + self_weight_factor) * Ps / A + 6 * abs(Mx_s) / (Bm * Lm ** 2) + 6 * abs(My_s) / (Lm * Bm ** 2)
    rep.step("أقصى جهد تشغيل على التربة", "q = (1+k)P/A + 6Mx/(B·L²) + 6My/(L·B²)", "", q_s, "kN/m²")
    rep.check("جهد التشغيل ≤ جهد التربة المسموح", q_s, q_allow, "kN/m²",
              P.Ref("كود الأساسات 202 / تقرير التربة", None, False, "كود 202 غير موجود في المرجع"))
    q_min = (1 + self_weight_factor) * Ps / A - 6 * abs(Mx_s) / (Bm * Lm ** 2) - 6 * abs(My_s) / (Lm * Bm ** 2)
    if q_min < 0:
        rep.note("فيه شد تحت القاعدة (qmin < 0): المعادلات الخطية غير صالحة، كبّر القاعدة.")

    k_u = Pu / Ps
    qu = rep.step("جهد التربة الأقصى الصافي qu (للتصميم الخرساني)",
                  "qu = Pu/A + (Pu/Ps)·(6Mx/(B·L²) + 6My/(L·B²))", "",
                  Pu / A + k_u * (6 * abs(Mx_s) / (Bm * Lm ** 2) + 6 * abs(My_s) / (Lm * Bm ** 2)),
                  "kN/m²")
    qu_Nmm2 = qu / 1e3  # kN/m² → N/mm²

    # -------- السمك (من القص الثاقب والقص في اتجاه واحد)
    s = P.sqrt_fcu_gc(fcu)
    qcu = P.QCU_UNCRACKED * s
    auto_h = h is None
    h_try = h or 400.0
    while True:
        d = h_try - cover - 16
        a1, b1 = col_a + d, col_b + d
        bo = 2 * (a1 + b1)
        Qup = Pu * 1e3 - qu_Nmm2 * a1 * b1
        qup = Qup / (bo * d)
        qcup, _ = punching_strength(fcu, d, bo, col_a, col_b, location)
        xL = (Lf - col_b) / 2 - d / 2
        xB = (B - col_a) / 2 - d / 2
        q1L = qu_Nmm2 * B * max(xL, 0) / (B * d)
        q1B = qu_Nmm2 * Lf * max(xB, 0) / (Lf * d)
        if (qup <= qcup and max(q1L, q1B) <= qcu) or not auto_h or h_try > 2500:
            break
        h_try += 50
    h = h_try
    rep.step("سمك القاعدة h", "", "أقل سمك يحقق القص الثاقب والقص في اتجاه واحد (بخطوات 50 مم)" if auto_h else "مُدخل",
             float(h), "mm")
    d = rep.step("العمق الفعال d", "d = h − cover − Ø", f"{h} − {cover} − 16", h - cover - 16, "mm")

    # القص الثاقب
    rep.step("— القص الثاقب (على بعد d/2 من وش العمود) —", "", "", "", "")
    a1, b1 = col_a + d, col_b + d
    bo = rep.step("محيط القطاع الحرج bo", "bo = 2[(a + d) + (b + d)]", f"2[({col_a}+{d:.0f}) + ({col_b}+{d:.0f})]",
                  2 * (a1 + b1), "mm", P.REF_PUNCH)
    Qup = rep.step("قوة القص الثاقب Qup", "Qup = Pu − qu·(a + d)(b + d)",
                   f"{Pu:.1f} − {qu:.1f}×{a1/1000:.3f}×{b1/1000:.3f}", Pu - qu * a1 * b1 / 1e6, "kN", P.REF_PUNCH)
    qup = rep.step("إجهاد القص الثاقب qup", "qup = Qup / (bo·d)", f"{Qup:.1f}×10³/({bo:.0f}×{d:.0f})",
                   Qup * 1e3 / (bo * d), "N/mm²", P.Ref("بند 4-2-2-3 معادلة 4-44", 105))
    qcup, (q1, q2, q3) = punching_strength(fcu, d, bo, col_a, col_b, location)
    rep.step("مقاومة القص الثاقب qcup", "min[0.8(αd/bo + 0.2)√(fcu/γc) , 0.316(0.5 + a/b)√(fcu/γc) , 0.316√(fcu/γc) , 1.7]",
             f"min({q1:.3f} , {q2:.3f} , {q3:.3f} , 1.7)  α={P.PUNCH_ALPHA[location]:.0f}", qcup, "N/mm²", P.REF_PUNCH)
    rep.check("qup ≤ qcup", qup, qcup, "N/mm²", P.REF_PUNCH)

    # القص في اتجاه واحد
    rep.step("— القص في اتجاه واحد (على بعد d/2 من وش العمود) —", "", "", "", "")
    rep.step("مقاومة الخرسانة للقص qcu", "qcu = 0.16√(fcu/γc)", f"0.16×√({fcu}/1.5)", qcu, "N/mm²", P.REF_QCU_UNC)
    ref_1w = P.Ref("بند 4-2-2-2 (القواعد تقاوم القص بالخرسانة فقط) — القطاع الحرج عند d/2", 104, False,
                   "موقع القطاع الحرج للقص في اتجاه واحد في القواعد: راجع الكود")
    for name, width, over in (("اتجاه L", B, (Lf - col_b) / 2), ("اتجاه B", Lf, (B - col_a) / 2)):
        x = max(over - d / 2, 0)
        Q = qu * (width / 1000) * (x / 1000)
        q = rep.step(f"إجهاد القص ({name})", "q = qu·W·(x − d/2) / (W·d)", f"{Q:.1f}×10³/({width:.0f}×{d:.0f})",
                     Q * 1e3 / (width * d), "N/mm²", ref_1w)
        rep.check(f"q ≤ qcu ({name})", q, qcu, "N/mm²", P.REF_QCU_UNC)

    # العزوم والتسليح
    rep.step("— العزوم والتسليح (عند وش العمود) —", "", "", "", "")
    res = {"B × L × h": f"{B:.0f} × {Lf:.0f} × {h:.0f} mm", "qu_kN_m2": round(qu, 1)}
    sc = P.STRESS_BLOCK * fcu / P.GAMMA_C
    fd = P.fyd(fy)
    for name, width, over, key in (("موازي لـ L (عزم في اتجاه L)", B, (Lf - col_b) / 2, "bars_along_L"),
                                   ("موازي لـ B (عزم في اتجاه B)", Lf, (B - col_a) / 2, "bars_along_B")):
        Mu = rep.step(f"العزم عند وش العمود — تسليح {name}", "Mu = qu·W·x²/2",
                      f"{qu:.1f}×{width/1000:.2f}×{over/1000:.3f}²/2", qu * (width / 1000) * (over / 1000) ** 2 / 2,
                      "kN·m")
        bm = 1000.0
        Mu_m = Mu / (width / 1000)
        disc = d * d - 2 * Mu_m * 1e6 / (sc * bm)
        a = d - math.sqrt(max(disc, 0))
        a = max(a, P.A_MIN_OVER_D * d)
        As = rep.step(f"As لكل متر ({name})", "As = Mu/(fy/γs·(d − a/2)) ، a ≥ 0.1d",
                      f"{Mu_m*1e6:.3e}/({fd:.1f}×{min(d - a/2, 0.95*d):.1f})",
                      Mu_m * 1e6 / (fd * min(d - a / 2, P.LEVER_MAX * d)), "mm²/m", P.REF_A_MIN)
        As_min = min_flexural_steel(fcu, fy, bm, d, As, rep)
        As_d = max(As, As_min)
        for dia in (12, 14, 16, 18, 20, 22, 25):
            n = max(5, math.ceil(As_d / bar_area(dia)))
            if 1000 / n >= 100:
                break
        res[key] = f"{n}Ø{dia}/m (As = {n*bar_area(dia):.0f} mm²/m ≥ {As_d:.0f})"
        rep.step(f"التسليح المختار ({name})", "", "", res[key], "")
        Ld, fbu = development_length(fy, fcu, dia)
        avail = over - cover
        rep.step(f"طول التماسك Ld (Ø{dia})", "Ld = α·β·η·(fy/γs)·Ø / (4·fbu) ، fbu = 0.30√(fcu/γc)",
                 f"1×{P.BETA_DEFORMED}×1×{fd:.1f}×{dia}/(4×{fbu:.3f})", Ld, "mm", P.REF_LD)
        if not rep.check(f"الطول المتاح ≥ Ld ({name})", avail, Ld, "mm", P.REF_LD, "≥"):
            rep.note(f"الطول المستقيم غير كافي ({name}): اعمل جنش 90° في أطراف الأسياخ أو قلل القطر.")

    rep.results = res
    return rep
