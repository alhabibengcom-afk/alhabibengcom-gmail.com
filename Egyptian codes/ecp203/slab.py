"""البلاطات المصمتة والمسطحة (غير سابقة الإجهاد) - ECP 203-2020.

- بلاطات اتجاه واحد بمعاملات العزوم.
- بلاطات اتجاهين بالطريقة المبسطة (α، β) للأحمال الحية ≤ 5 kN/m².
- تصميم شريحة بعرض متر لعزوم جاية من برنامج (SAFE / ETABS) — للبلاطات المسطحة وغيرها.
- القص الثاقب للبلاطات المسطحة (الخرسانة فقط).

الأحمال بالـ kN/m²، البحور بالمتر، السمك بالمم.
"""
from __future__ import annotations

import math

from . import params as P
from .bars import bar_area
from .footing import punching_strength
from .report import Report


# ------------------------------------------------------------------ تصميم شريحة متر
def strip_steel(Mu, t, fcu, fy, rep: Report, label="", cover=20.0, dia_guess=12):
    """As (mm²/m) لعزم Mu (kN·m/m)، مع الحد الأدنى وتوزيع الأسياخ."""
    d = t - cover - dia_guess / 2
    sc = P.STRESS_BLOCK * fcu / P.GAMMA_C
    fd = P.fyd(fy)
    b = 1000.0
    Mu_N = abs(Mu) * 1e6
    disc = d * d - 2 * Mu_N / (sc * b)
    if disc < 0:
        rep.check(f"السمك كافي للعزم {label}", Mu_N, sc * b * d * d / 2, "N·mm")
        return None
    a = max(d - math.sqrt(disc), P.A_MIN_OVER_D * d)
    c = a / P.BETA1
    from .beam import cmax_over_d
    rep.check(f"c/d ≤ cmax/d {label}", c / d, cmax_over_d(fy), "", P.REF_CMAX)
    lever = min(d - a / 2, P.LEVER_MAX * d)
    As = rep.step(f"As {label}", "As = Mu / (fy/γs · (d − a/2))",
                  f"{Mu_N:.3e}/({fd:.1f}×{lever:.1f})", Mu_N / (fd * lever), "mm²/m", P.REF_A_MIN)
    rho_abs = P.MIN_RHO_ABS_MILD if P.is_mild(fy) else P.MIN_RHO_ABS_HT
    As_min = rep.step(f"As,min {label}", "max(0.6/fy · b·d , ρabs · b·t)",
                      f"max(0.6/{fy}×1000×{d:.0f} , {rho_abs}×1000×{t})",
                      max(P.SLAB_MIN_RHO_NUM / fy * b * d, rho_abs * b * t), "mm²/m", P.REF_SLAB_MIN)
    return pick_mesh(max(As, As_min), rep, label)


def pick_mesh(As, rep: Report, label=""):
    for dia in (8, 10, 12, 14, 16, 18, 20):
        n = max(P.SLAB_MIN_BARS_PER_M, math.ceil(As / bar_area(dia)))
        if 1000 / n <= P.SLAB_MAX_SPACING and 1000 / n >= 100:
            break
    txt = f"{n}Ø{dia}/m ({n*bar_area(dia):.0f} mm²/m)"
    rep.step(f"التسليح المختار {label}", "≥ 5 أسياخ/م ، مسافة ≤ 200 مم", f"As = {As:.0f}", txt, "",
             P.REF_SLAB_SPACING)
    return {"As_mm2_m": round(As, 0), "bars": txt, "provided_mm2_m": n * bar_area(dia)}


def factored(wD, wL, rep: Report):
    return rep.step("الحمل الأقصى wu", "wu = 1.4 D + 1.6 L", f"1.4×{wD} + 1.6×{wL}",
                    P.LOAD_D * wD + P.LOAD_L * wL, "kN/m²", P.REF_LOADS)


# ------------------------------------------------------------------ اتجاه واحد
def design_one_way_slab(L, wD, wL, support="both_ends", t=None, fcu=25, fy=400, cover=20.0,
                        title=None):
    """support: simple | one_end | both_ends | cantilever. L = البحر الفعال (m).
    wD يشمل وزن البلاطة والتشطيبات (kN/m²)."""
    rep = Report(title or f"بلاطة اتجاه واحد — بحر {L} م ({support}) — ECP 203-2020")
    rep.inputs = {"البحر الفعال": f"{L} m", "الارتكاز": support, "wD / wL": f"{wD} / {wL} kN/m²",
                  "fcu / fy": f"{fcu} / {fy} N/mm²", "الغطاء": f"{cover} mm"}
    div = P.SLAB_T_MIN_ONEWAY[support]
    t_min = rep.step("أقل سمك", f"t ≥ L/{div:.0f} ≥ {P.SLAB_T_ABS_MIN:.0f} mm", f"{L*1000:.0f}/{div:.0f}",
                     max(L * 1000 / div, P.SLAB_T_ABS_MIN), "mm", P.REF_SLAB_T_ONEWAY)
    if t is None:
        t = float(math.ceil(t_min / 10) * 10)
        rep.step("السمك المختار", "", "مقرب لأعلى 10 مم", t, "mm")
        rep.note("وزن البلاطة لازم يكون متضمن في wD بنفس السمك المختار.")
    rep.check("t ≥ tmin", t, t_min, "mm", P.REF_SLAB_T_ONEWAY, "≥")
    wu = factored(wD, wL, rep)
    if wL > 2 * wD:
        rep.note("الحمل الحي أكبر من ضعف الميت: معاملات العزوم المبسطة غير صالحة، حلل البلاطة كمرة مستمرة.")
    res = {"t_mm": t, "wu_kN_m2": round(wu, 2)}
    if support == "cantilever":
        Mneg = rep.step("العزم السالب عند الركيزة", "M = wu·L²/2", f"{wu:.2f}×{L}²/2", wu * L * L / 2, "kN·m/m")
        main = strip_steel(Mneg, t, fcu, fy, rep, "(علوي — كابولي)", cover)
        res["top"] = main and main["bars"]
    else:
        kp, kn = P.SLAB_K[support]
        Mpos = rep.step("العزم الموجب", f"M+ = wu·L²/{kp:.0f}", f"{wu:.2f}×{L}²/{kp:.0f}", wu * L * L / kp,
                        "kN·m/m", P.REF_SLAB_K)
        main = strip_steel(Mpos, t, fcu, fy, rep, "(سفلي)", cover)
        res["bottom"] = main and main["bars"]
        if kn:
            Mneg = rep.step("العزم السالب عند الركيزة المستمرة", f"M− = wu·L²/{kn:.0f}", f"{wu:.2f}×{L}²/{kn:.0f}",
                            wu * L * L / kn, "kN·m/m", P.REF_SLAB_K)
            top = strip_steel(Mneg, t, fcu, fy, rep, "(علوي)", cover)
            res["top"] = top and top["bars"]
        rep.note("لو البلاطة أول بحر مستمر، العزم السالب عند أول ركيزة داخلية wL²/10 (شكل 6-2).")
    if main:
        sec = rep.step("تسليح التوزيع (العمودي على الرئيسي)", "As,sec ≥ 20% As,main",
                       f"0.20×{main['provided_mm2_m']:.0f}", P.SLAB_SECONDARY_ONEWAY * main["provided_mm2_m"],
                       "mm²/m", P.REF_SLAB_SECONDARY)
        res["distribution"] = pick_mesh(sec, rep, "(توزيع)")["bars"]
    # القص
    Qu = wu * L * (1.0 if support == "cantilever" else 0.5 if support == "simple" else 0.6)
    d = t - cover - 6
    qu = rep.step("إجهاد القص (تقريبي عند الركيزة)", "qu = Qu/(1000·d)", f"{Qu:.1f}×10³/(1000×{d:.0f})",
                  Qu * 1e3 / (1000 * d), "N/mm²")
    rep.check("qu ≤ qcu (البلاطات تقاوم القص بالخرسانة فقط)", qu, P.QCU_UNCRACKED * P.sqrt_fcu_gc(fcu), "N/mm²",
              P.REF_QCU_UNC)
    rep.results = res
    return rep


# ------------------------------------------------------------------ اتجاهين
def design_two_way_slab(a, b, wD, wL, cont_a=2, cont_b=2, t=None, fcu=25, fy=400, cover=20.0, title=None):
    """a = البحر القصير، b = الطويل (m). cont_a / cont_b = عدد الجوانب المستمرة (0..2)
    في اتجاه البحر a وفي اتجاه البحر b. البلاطة مصبوبة مع الكمرات، والحمل الحي ≤ 5 kN/m²."""
    if a > b:
        a, b, cont_a, cont_b = b, a, cont_b, cont_a
    rep = Report(title or f"بلاطة اتجاهين {a}×{b} م — ECP 203-2020")
    rep.inputs = {"a × b": f"{a} × {b} m", "جوانب مستمرة (اتجاه a / b)": f"{cont_a} / {cont_b}",
                  "wD / wL": f"{wD} / {wL} kN/m²", "fcu / fy": f"{fcu} / {fy} N/mm²"}
    ma, mb = P.SLAB_M[cont_a], P.SLAB_M[cont_b]
    r = rep.step("نسبة المستطيلية r", "r = (mb·b)/(ma·a)", f"({mb}×{b})/({ma}×{a})", mb * b / (ma * a), "",
                 P.REF_SLAB_M)
    if r > P.TWO_WAY_R_MAX:
        rep.note(f"r = {r:.2f} > 2: البلاطة تُصمم اتجاه واحد في البحر القصير.")
        return design_one_way_slab(a, wD, wL, {0: "simple", 1: "one_end", 2: "both_ends"}[cont_a], t, fcu, fy, cover)
    if wL > 5:
        rep.note("الحمل الحي > 5 kN/m²: الكود بيستخدم جدول 6-2 بدل معادلة α و β — النتيجة هنا تقريبية.")
    cont_min = min(cont_a, cont_b)
    div = P.SLAB_T_MIN_TWOWAY[cont_min]
    t_min = rep.step("أقل سمك", f"t ≥ a/{div:.0f} ≥ {P.SLAB_T_ABS_MIN:.0f}", f"{a*1000:.0f}/{div:.0f}",
                     max(a * 1000 / div, P.SLAB_T_ABS_MIN), "mm", P.REF_SLAB_T_TWOWAY)
    if t is None:
        t = float(math.ceil(t_min / 10) * 10)
    rep.check("t ≥ tmin", t, t_min, "mm", P.REF_SLAB_T_TWOWAY, "≥")
    wu = factored(wD, wL, rep)
    alpha = rep.step("معامل توزيع الحمل α (البحر القصير)", "α = 0.5 r − 0.15", f"0.5×{r:.3f} − 0.15",
                     0.5 * r - 0.15, "", P.REF_ALPHA_BETA)
    beta = rep.step("معامل توزيع الحمل β (البحر الطويل)", "β = 0.35 / r²", f"0.35/{r:.3f}²", 0.35 / r ** 2, "",
                    P.REF_ALPHA_BETA)
    K = {0: (8, None), 1: (10, 10), 2: (12, 12)}
    res = {"t_mm": t, "r": round(r, 3)}
    for name, coef, span, cont, dir_ in (("a", alpha, a, cont_a, "short"), ("b", beta, b, cont_b, "long")):
        kp, kn = K[cont]
        Mp = rep.step(f"العزم الموجب في اتجاه {name}", f"M = {('α' if name=='a' else 'β')}·wu·{name}²/{kp}",
                      f"{coef:.3f}×{wu:.2f}×{span}²/{kp}", coef * wu * span ** 2 / kp, "kN·m/m", P.REF_ALPHA_BETA)
        cov = cover if dir_ == "short" else cover + 10
        s = strip_steel(Mp, t, fcu, fy, rep, f"(سفلي اتجاه {name})", cov)
        res[f"bottom_{name}"] = s and s["bars"]
        if kn:
            Mn = rep.step(f"العزم السالب في اتجاه {name}", f"M = {('α' if name=='a' else 'β')}·wu·{name}²/{kn}",
                          f"{coef:.3f}×{wu:.2f}×{span}²/{kn}", coef * wu * span ** 2 / kn, "kN·m/m",
                          P.REF_ALPHA_BETA)
            s2 = strip_steel(Mn, t, fcu, fy, rep, f"(علوي اتجاه {name})", cover)
            res[f"top_{name}"] = s2 and s2["bars"]
    rep.note("التسليح في الاتجاه الطويل بيتحط فوق القصير (d أقل بـ 10 مم تقريباً).")
    rep.note("عند اختلاف العزم السالب بين بلاطتين متجاورتين، خد المتوسط المرجح (معادلة 6-9).")
    rep.results = res
    return rep


# ------------------------------------------------------------------ شريحة من برنامج
def design_slab_strip(t, fcu, fy, Mu_pos=0.0, Mu_neg=0.0, cover=20.0, title=None):
    """عزوم قصوى لكل متر (kN·m/m) من التحليل بالبرامج — للبلاطات المسطحة أو أي بلاطة."""
    rep = Report(title or f"تصميم شريحة بلاطة سمك {t} مم — ECP 203-2020")
    rep.inputs = {"t": f"{t} mm", "Mu+ / Mu−": f"{Mu_pos} / {Mu_neg} kN·m/m", "fcu / fy": f"{fcu} / {fy}"}
    res = {}
    if Mu_pos:
        s = strip_steel(Mu_pos, t, fcu, fy, rep, "(سفلي)", cover)
        res["bottom"] = s and s["bars"]
    if Mu_neg:
        s = strip_steel(Mu_neg, t, fcu, fy, rep, "(علوي)", cover)
        res["top"] = s and s["bars"]
    rep.results = res
    return rep


# ------------------------------------------------------------------ القص الثاقب
def check_flat_slab_punching(c1, c2, t, Vu, fcu=30, location="interior", cover=20.0, beta=None, title=None):
    """Vu = رد فعل العمود الأقصى ناقص الحمل داخل القطاع الحرج (kN) — أو رد الفعل كله (متحفظ)."""
    rep = Report(title or f"القص الثاقب — عمود {c1}×{c2} مم، بلاطة {t} مم — ECP 203-2020")
    rep.inputs = {"العمود": f"{c1} × {c2} mm", "t": f"{t} mm", "Vu": f"{Vu} kN", "fcu": fcu, "الموقع": location}
    d = t - cover - 12
    rep.step("العمق الفعال d (متوسط الاتجاهين)", "d = t − cover − Ø", f"{t} − {cover} − 12", d, "mm")
    if location == "interior":
        bo = 2 * (c1 + d) + 2 * (c2 + d)
    elif location == "edge":
        bo = 2 * (c1 + d / 2) + (c2 + d)
    else:
        bo = (c1 + d / 2) + (c2 + d / 2)
    rep.step("محيط القطاع الحرج bo (على d/2)", "", "", bo, "mm", P.Ref("بند 4-2-2-3 شكل 4-13", 106))
    beta = beta or P.PUNCH_BETA[location]
    qup = rep.step("إجهاد القص الثاقب qup", "qup = β·Vu / (bo·d)", f"{beta}×{Vu}×10³/({bo:.0f}×{d:.0f})",
                   beta * Vu * 1e3 / (bo * d), "N/mm²", P.REF_PUNCH_BETA)
    qcup, (q1, q2, q3) = punching_strength(fcu, d, bo, c1, c2, location)
    rep.step("مقاومة القص الثاقب qcup", "min[0.8(αd/bo + 0.2)√(fcu/γc) , 0.316(0.5 + a/b)√(fcu/γc) , 0.316√(fcu/γc) , 1.7]",
             f"min({q1:.3f} , {q2:.3f} , {q3:.3f} , 1.7)", qcup, "N/mm²", P.REF_PUNCH)
    rep.check("qup ≤ qcup", qup, qcup, "N/mm²", P.REF_PUNCH)
    if qup > qcup:
        d_need = d
        while d_need < 3 * d:
            d_need += 10
            bo2 = bo + (8 if location == "interior" else 3 if location == "edge" else 1) * (d_need - d) / 2
            if beta * Vu * 1e3 / (bo2 * d_need) <= punching_strength(fcu, d_need, bo2, c1, c2, location)[0]:
                break
        rep.note(f"مطلوب تقريباً d ≈ {d_need:.0f} مم (t ≈ {d_need + cover + 12:.0f} مم)، أو تيجان/سقوط، أو كانات قص ثاقب (بشرط السمك الأدنى في بند 4-2-2-3 فقرة 1-ب، صفحة 105).")
    rep.results = {"qup": round(qup, 3), "qcup": round(qcup, 3), "ratio": round(qup / qcup, 2)}
    return rep
