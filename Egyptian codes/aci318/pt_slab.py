"""مراجعة بلاطات البوست تنشن ذات الاتجاهين طبقاً لـ ACI 318-19 (SI).

المكتبة دي بتراجع قطاع (شريحة تصميم) بقيم جاية من التحليل (SAFE / ADAPT / RAM):
- إجهادات النقل (Transfer) والتشغيل (Service) — Class U.
- أقل ضغط مسبق متوسط.
- أقل تسليح عادي مترابط (Table 8.6.2.3).
- المقاومة القصوى للعزم مع العزوم الثانوية (Secondary / Hyperstatic).
- حدود إجهاد الكابلات.
- القص الثاقب (22.6.5.5 للبوست تنشن، أو 22.6.5.2).

الإشارات: الشد موجب. العزوم موجبة للعزم الموجب (Sagging). e موجبة أسفل محور القطاع.
الوحدات: mm، kN، kN·m، MPa.
"""
from __future__ import annotations

import math

from ecp203.params import Ref
from ecp203.report import Report


def R(clause, page=None, verified=True, note=""):
    return Ref(clause, page, verified, note, code="ACI 318-19")


# ------------------------------------------------------------------ المعاملات (اتراجعت على صور الكود)
LOAD = R("Table 5.3.1 Eq. (5.3.1a,b): U = 1.4D ، U = 1.2D + 1.6L", 103)
SECONDARY = R("5.3.11 (العزوم الثانوية ضمن U بمعامل 1.0)", 107, False, "معامل 1.0 ممارسة شائعة؛ راجع R5.3.11")
CLASS_U = R("8.3.4.1: Class U مع ft ≤ 0.5√fc′", 165)
TRANSFER_C = R("Table 24.5.3.1 (0.60 fci′ عامة، 0.70 fci′ لأطراف البسيط)", 723)
TRANSFER_T = R("Table 24.5.3.2 (0.25√fci′ عامة، 0.5√fci′ لأطراف البسيط)", 724)
SERVICE_C = R("Table 24.5.4.1 (0.45 fc′ مستديم، 0.60 fc′ كلي)", 725)
FPC_MIN = R("8.6.2.1 (أقل ضغط مسبق متوسط 0.9 MPa)", 181)
AS_MIN = R("Table 8.6.2.3 (أقل تسليح مترابط في البلاطات ذات الاتجاهين)", 182)
AS_MIN_DETAIL = R("8.7.5.3 (توزيع في عرض c2 + 2×1.5h، 4 أسياخ على الأقل، مسافة ≤ 300 مم)", 190)
FPS_UNB = R("Table 20.3.2.4.1 (fps للكابلات غير المترابطة)", 591)
FPS_BONDED = R("20.3.2.3.1 Eq. (20.3.2.3.1)", 589, False, "المعادلة من الذاكرة (γp = 0.28 للمنخفض الاسترخاء)؛ راجع الصورة")
TENDON = R("Table 20.3.2.5.1 (0.94fpy و 0.80fpu عند الشد، 0.70fpu بعد النقل)", 591)
PHI = R("Table 21.2.1 (φ = 0.90 انحناء مضبوط بالشد، 0.75 قص)", 605)
PHI_TC = R("21.2.2 (εt ≥ 0.005 → tension-controlled)", 606, False, "حد 0.005 من الذاكرة؛ راجع الجدول 21.2.2")
BETA1 = R("Table 22.2.2.4.3 (β1)", 615)
PUNCH_PT = R("22.6.5.4 و 22.6.5.5 (a,b) و 22.6.5.3 (αs = 40/30/20)", 645)
PUNCH_RC = R("Table 22.6.5.2", 643)
LAMBDA_S = R("22.5.5.1.3: λs = √(2/(1 + 0.004d)) ≤ 1", 626, False, "المعادلة من الذاكرة؛ النص المستخرج ناقص")
GAMMA_V = R("8.4.4.2.2 و R8.4.4.2.3 (γv = 1 − γf ، Jc)", 174, False,
            "γf = 1/(1 + (2/3)√(b1/b2)) من 8.4.2.2.2 من الذاكرة؛ Jc اتراجعت على الشكل")

ALPHA_S = {"interior": 40, "edge": 30, "corner": 20}


def beta1(fc):
    if fc <= 28:
        return 0.85
    return max(0.65, 0.85 - 0.05 * (fc - 28) / 7)


# ------------------------------------------------------------------ مساعدات
def fiber_stresses(P_N, M_Nmm, A, S):
    """(f_top, f_bot) بالـ MPa — الشد موجب، M موجب = Sagging (شد في الأسفل)."""
    return -P_N / A - M_Nmm / S, -P_N / A + M_Nmm / S


def _stage(rep, name, P_kN, M_kNm, e, M2_kNm, A, S):
    M_net = M_kNm * 1e6 + M2_kNm * 1e6 - P_kN * 1e3 * e
    ft, fb = fiber_stresses(P_kN * 1e3, M_net, A, S)
    rep.step(f"{name}: العزم الصافي", "Mnet = Mext + M2 − P·e",
             f"{M_kNm:.1f} + {M2_kNm:.1f} − {P_kN:.0f}×{e/1000:.3f}", M_net / 1e6, "kN·m")
    rep.step(f"{name}: إجهاد الألياف العلوية", "ftop = −P/A − Mnet/S", "", ft, "MPa")
    rep.step(f"{name}: إجهاد الألياف السفلية", "fbot = −P/A + Mnet/S", "", fb, "MPa")
    return ft, fb


# ------------------------------------------------------------------ مراجعة القطاع
def check_pt_section(b, h, fc, Aps, Pe, e, M_D, M_L, M_SDL=0.0, M2=0.0, fci=None, Pi=None, M_sw=None,
                     region="positive", span=None, fpu=1860.0, fpy=None, fy=420.0, As=0.0, cover=25.0,
                     bonded=False, sustained_L=0.0, Pj=None, frame_width=None, column_width=None, title=None):
    """b = عرض الشريحة (mm)، Aps = مساحة الكابلات في الشريحة (mm²)، Pe/Pi/Pj بالـ kN،
    e = لامركزية الكابل عند القطاع (mm، موجبة لأسفل)، span = البحر (m) لحساب ℓn/h،
    region = positive | negative، frame_width = عرض شريحة الإطار المكافئ l2 (mm) للـ Acf."""
    rep = Report(title or f"مراجعة قطاع بوست تنشن ({'موجب' if region == 'positive' else 'سالب'}) — ACI 318-19")
    fpy = fpy or 0.9 * fpu
    fci = fci or 0.75 * fc
    Pi = Pi or Pe / 0.85
    M_sw = M_D if M_sw is None else M_sw
    rep.inputs = {"b × h": f"{b} × {h} mm", "fc′ / fci′": f"{fc} / {fci} MPa", "Aps": f"{Aps} mm²",
                  "Pi / Pe": f"{Pi:.0f} / {Pe:.0f} kN", "e": f"{e} mm", "MD / MSDL / ML": f"{M_D} / {M_SDL} / {M_L} kN·m",
                  "M2 (ثانوي، تشغيل)": f"{M2} kN·m", "المنطقة": region, "نوع الكابلات": "مترابطة" if bonded else "غير مترابطة",
                  "fpu / fpy": f"{fpu} / {fpy:.0f} MPa", "As (عادي موجود)": f"{As} mm²"}
    if Pi == Pe / 0.85:
        rep.note("Pi مش مُدخلة: اتفرضت Pe/0.85 (فواقد طويلة المدى 15%). دخّل القيمة الفعلية من حسابات الفواقد.")
    A, S = b * h, b * h * h / 6
    sq = math.sqrt(fc)

    # ---- أقل ضغط مسبق
    rep.step("— الضغط المسبق المتوسط —", "", "", "", "")
    fpc = rep.step("fpc = Pe / A", "fpc = Pe/(b·h)", f"{Pe}×10³/({b}×{h})", Pe * 1e3 / A, "MPa", FPC_MIN)
    rep.check("fpc ≥ 0.9 MPa", fpc, 0.9, "MPa", FPC_MIN, "≥")

    # ---- حدود الكابلات
    rep.step("— إجهاد الكابلات —", "", "", "", "")
    if Pj:
        fpj = rep.step("إجهاد الشد عند الجاك", "fpj = Pj/Aps", f"{Pj}×10³/{Aps}", Pj * 1e3 / Aps, "MPa", TENDON)
        rep.check("fpj ≤ min(0.94fpy , 0.80fpu)", fpj, min(0.94 * fpy, 0.80 * fpu), "MPa", TENDON)
    fpi = rep.step("الإجهاد بعد النقل", "fpi = Pi/Aps", f"{Pi:.0f}×10³/{Aps}", Pi * 1e3 / Aps, "MPa", TENDON)
    rep.check("fpi ≤ 0.70 fpu (عند المراسي)", fpi, 0.70 * fpu, "MPa", TENDON)

    # ---- النقل
    rep.step("— مرحلة النقل (Pi + الوزن الذاتي) —", "", "", "", "")
    ft, fb = _stage(rep, "النقل", Pi, M_sw, e, M2 * Pi / Pe, A, S)
    rep.check("ضغط النقل ≤ 0.60 fci′", -min(ft, fb), 0.60 * fci, "MPa", TRANSFER_C)
    rep.check("شد النقل ≤ 0.25√fci′", max(ft, fb), 0.25 * math.sqrt(fci), "MPa", TRANSFER_T)
    if max(ft, fb) > 0.25 * math.sqrt(fci):
        rep.note("شد النقل أكبر من الحد: لازم تسليح مترابط يشيل كل قوة الشد (24.5.3.2.1)، أو عدّل الكابلات.")

    # ---- التشغيل
    rep.step("— مرحلة التشغيل (Pe + كل الأحمال) —", "", "", "", "")
    Mtot = M_D + M_SDL + M_L
    ft, fb = _stage(rep, "التشغيل الكلي", Pe, Mtot, e, M2, A, S)
    rep.check("ضغط التشغيل الكلي ≤ 0.60 fc′", -min(ft, fb), 0.60 * fc, "MPa", SERVICE_C)
    rep.check("شد التشغيل ≤ 0.5√fc′ (Class U)", max(ft, fb), 0.5 * sq, "MPa", CLASS_U)
    Msus = M_D + M_SDL + sustained_L * M_L
    fts, fbs = _stage(rep, "التشغيل المستديم", Pe, Msus, e, M2, A, S)
    rep.check("ضغط التشغيل المستديم ≤ 0.45 fc′", -min(fts, fbs), 0.45 * fc, "MPa", SERVICE_C)

    # ---- أقل تسليح مترابط
    rep.step("— أقل تسليح عادي مترابط —", "", "", "", "")
    fy_m = min(fy, 420.0)
    if region == "positive":
        f_t = fb
        f_c = -ft
        if f_t <= 0.17 * sq:
            As_min = rep.step("ft ≤ 0.17√fc′ → غير مطلوب", "", f"ft = {f_t:.3f} ≤ {0.17*sq:.3f}", 0.0, "mm²", AS_MIN)
        else:
            y = h * f_t / (f_t + max(f_c, 0)) if f_c > 0 else h
            Nc = rep.step("قوة الشد Nc", "Nc = ½·ft·y·b ، y = h·ft/(ft + fc)", f"0.5×{f_t:.3f}×{y:.1f}×{b}",
                          0.5 * f_t * y * b / 1e3, "kN", AS_MIN)
            As_min = rep.step("As,min", "As,min = Nc / (0.5 fy)", f"{Nc:.1f}×10³/(0.5×{fy_m})",
                              Nc * 1e3 / (0.5 * fy_m), "mm²", AS_MIN)
    else:
        Acf = h * (frame_width or b)
        As_min = rep.step("As,min عند الأعمدة", "As,min = 0.00075·Acf ، Acf = h·l2", f"0.00075×{h}×{frame_width or b}",
                          0.00075 * Acf, "mm²", AS_MIN)
        if column_width:
            rep.step("عرض توزيع التسليح العلوي", "c2 + 2×1.5h", f"{column_width} + 3×{h}", column_width + 3 * h, "mm",
                     AS_MIN_DETAIL)
        rep.note("التسليح العلوي عند الأعمدة: 4 أسياخ على الأقل، والمسافة ≤ 300 مم (8.7.5.3).")
        if not frame_width:
            rep.note("frame_width مش مُدخل: Acf اتحسب بعرض الشريحة b. الصح هو أكبر l2 للإطارين المتقاطعين عند العمود.")

    # ---- المقاومة القصوى
    rep.step("— المقاومة القصوى للعزم —", "", "", "", "")
    Mu1 = 1.2 * (M_D + M_SDL) + 1.6 * M_L + 1.0 * M2
    Mu2 = 1.4 * (M_D + M_SDL) + 1.0 * M2
    sign = 1 if region == "positive" else -1
    Mu = rep.step("العزم الأقصى Mu", "max|1.2D + 1.6L + 1.0M2 , 1.4D + 1.0M2| (بإشارة المنطقة)",
                  f"1.2×{M_D + M_SDL} + 1.6×{M_L} + {M2}", max(sign * Mu1, sign * Mu2), "kN·m", LOAD)
    rep.note(f"العزم الثانوي M2 داخل في Mu بمعامل 1.0 ({SECONDARY}).")
    dp = h / 2 + sign * e
    ds = h - cover - 6
    rep.step("عمق الكابل من وش الضغط dp", "dp = h/2 ± e", f"{h}/2 {'+' if sign>0 else '−'} {abs(e)}", dp, "mm")
    fse = Pe * 1e3 / Aps
    rho_p = Aps / (b * dp)
    if bonded:
        fps = rep.step("fps (مترابطة)", "fps = fpu(1 − γp/β1 · ρp·fpu/fc′) ، γp = 0.28",
                       f"{fpu}(1 − 0.28/{beta1(fc):.3f}×{rho_p:.5f}×{fpu}/{fc})",
                       fpu * (1 - 0.28 / beta1(fc) * rho_p * fpu / fc), "MPa", FPS_BONDED)
    else:
        ratio = (span * 1000 / h) if span else 30
        if not span:
            rep.note("span مش مُدخل: اتفرض ℓn/h ≤ 35.")
        if ratio <= 35:
            vals = (fse + 70 + fc / (100 * rho_p), fse + 420, fpy)
            f_ = "min(fse + 70 + fc′/(100ρp) , fse + 420 , fpy)"
        else:
            vals = (fse + 70 + fc / (300 * rho_p), fse + 210, fpy)
            f_ = "min(fse + 70 + fc′/(300ρp) , fse + 210 , fpy)"
        fps = rep.step(f"fps (غير مترابطة، ℓn/h = {ratio:.1f})", f_,
                       f"min({vals[0]:.0f} , {vals[1]:.0f} , {vals[2]:.0f})  fse={fse:.0f} ρp={rho_p:.5f}",
                       min(vals), "MPa", FPS_UNB)
    b1 = beta1(fc)
    rep.step("β1", "Table 22.2.2.4.3", f"fc′ = {fc}", b1, "", BETA1)

    def capacity(As_):
        T = Aps * fps + As_ * fy_m
        a = T / (0.85 * fc * b)
        Mn = Aps * fps * (dp - a / 2) + As_ * fy_m * (ds - a / 2)
        c = a / b1
        eps_t = 0.003 * (max(dp, ds if As_ else dp) - c) / c
        return Mn / 1e6, a, eps_t

    As_use = max(As, As_min)
    Mn, a, eps_t = capacity(As_use)
    rep.step("عمق كتلة الضغط a", "a = (Aps·fps + As·fy)/(0.85 fc′·b)", f"({Aps}×{fps:.0f} + {As_use:.0f}×{fy_m})/(0.85×{fc}×{b})",
             a, "mm")
    phiMn = rep.step("φMn", "φ[Aps·fps(dp − a/2) + As·fy(ds − a/2)] ، φ = 0.90", f"0.9×{Mn:.1f}", 0.9 * Mn, "kN·m", PHI)
    rep.check("εt ≥ 0.005 (tension-controlled)", eps_t, 0.005, "", PHI_TC, "≥")
    As_req = As_use
    if phiMn < Mu:
        lo, hi = As_use, As_use + 50 * b
        for _ in range(100):
            mid = (lo + hi) / 2
            if 0.9 * capacity(mid)[0] < Mu:
                lo = mid
            else:
                hi = mid
        As_req = hi
        rep.step("التسليح العادي المطلوب للمقاومة", "حل φMn(As) = Mu", "", As_req, "mm²", PHI)
        Mn, a, eps_t = capacity(As_req)
        phiMn = 0.9 * Mn
    rep.check("Mu ≤ φMn (بالتسليح المطلوب)", Mu, phiMn, "kN·m", PHI)
    if As_req > As:
        rep.note(f"مطلوب تسليح عادي مترابط {As_req:.0f} mm² في منطقة الشد ({'سفلي' if sign > 0 else 'علوي'}).")

    rep.results = {"fpc_MPa": round(fpc, 2), "f_top/f_bot service (MPa)": f"{ft:.2f} / {fb:.2f}",
                   "As_min_mm2": round(As_min, 0), "As_required_mm2": round(As_req, 0),
                   "Mu_kNm": round(Mu, 1), "phiMn_kNm": round(phiMn, 1), "fps_MPa": round(fps, 0)}
    rep.note("الترخيم (24.2) وفواقد الشد مش محسوبين هنا: خدهم من برنامج التحليل.")
    return rep


# ------------------------------------------------------------------ القص الثاقب
def check_pt_punching(c1, c2, h, Vu, fc, fpc=None, location="interior", d=None, Vp=0.0, Msc=0.0,
                      near_edge=False, bonded_min_ok=True, title=None):
    """Vu (kN)، Msc = العزم غير المتوازن المنقول للعمود (kN·m) حول محور عمودي على c1 (للأعمدة الداخلية).
    fpc = متوسط الضغط المسبق في الاتجاهين (MPa)."""
    rep = Report(title or f"القص الثاقب لبلاطة بوست تنشن — عمود {c1}×{c2} مم — ACI 318-19")
    d = d or 0.8 * h
    rep.inputs = {"العمود c1 × c2": f"{c1} × {c2} mm", "h / d": f"{h} / {d:.0f} mm", "Vu": f"{Vu} kN",
                  "Msc": f"{Msc} kN·m", "fc′": f"{fc} MPa", "fpc": f"{fpc} MPa", "الموقع": location}
    if d == 0.8 * h:
        rep.note("d اتفرض 0.8h (22.6.2.2 يسمح بـ ≥ 0.8h للبوست تنشن).")
    if location == "interior":
        b1, b2 = c1 + d, c2 + d
        bo = 2 * (b1 + b2)
    elif location == "edge":
        b1, b2 = c1 + d / 2, c2 + d
        bo = 2 * b1 + b2
    else:
        b1, b2 = c1 + d / 2, c2 + d / 2
        bo = b1 + b2
    rep.step("محيط القطاع الحرج bo (على d/2)", "", "", bo, "mm", R("22.6.4.1", 639, False, "رقم الصفحة تقريبي"))
    vug = Vu * 1e3 / (bo * d)
    vu = rep.step("إجهاد القص من الحمل vug", "vug = Vu/(bo·d)", f"{Vu}×10³/({bo:.0f}×{d:.0f})", vug, "MPa")
    if Msc:
        if location != "interior":
            rep.note("نقل العزم للأعمدة الطرفية والركنية محتاج خصائص القطاع الحرج غير المتماثل: دخّل vu من البرنامج.")
        else:
            gf = 1 / (1 + 2 / 3 * math.sqrt(b1 / b2))
            gv = 1 - gf
            Jc = d * b1 ** 3 / 6 + b1 * d ** 3 / 6 + d * b2 * b1 ** 2 / 2
            vu = rep.step("إجهاد القص الأقصى مع نقل العزم", "vu = vug + γv·Msc·c/Jc",
                          f"{vug:.3f} + {gv:.3f}×{Msc}×10⁶×{b1/2:.0f}/{Jc:.3e}", vug + gv * Msc * 1e6 * (b1 / 2) / Jc,
                          "MPa", GAMMA_V)
    lam_s = min(1.0, math.sqrt(2 / (1 + 0.004 * d)))
    pt_ok = location == "interior" and not near_edge and fpc is not None and fpc >= 0.9 and bonded_min_ok
    if pt_ok:
        sq = min(math.sqrt(fc), 5.8)
        fpc_ = min(fpc, 3.5)
        a = 0.29 * sq + 0.3 * fpc_ + Vp * 1e3 / (bo * d)
        bb = 0.083 * (1.5 + ALPHA_S[location] * d / bo) * sq + 0.3 * fpc_ + Vp * 1e3 / (bo * d)
        vc = rep.step("vc (بوست تنشن)", "min[0.29√fc′ + 0.3fpc + Vp/(bo·d) , 0.083(1.5 + αs·d/bo)√fc′ + 0.3fpc + Vp/(bo·d)]",
                      f"min({a:.3f} , {bb:.3f})  √fc′ ≤ 5.8 ، fpc ≤ 3.5", min(a, bb), "MPa", PUNCH_PT)
    else:
        rep.note("شروط 22.6.5.4 مش متحققة (عمود غير داخلي، أو قريب من حافة < 4h، أو fpc < 0.9، أو مفيش تسليح 8.6.2.3): "
                 "اتستخدم جدول 22.6.5.2 للخرسانة غير سابقة الإجهاد.")
        beta = max(c1, c2) / min(c1, c2)
        sq = math.sqrt(fc)
        vals = (0.33 * lam_s * sq, (0.17 + 0.33 / beta) * lam_s * sq,
                (0.17 + 0.083 * ALPHA_S[location] * d / bo) * lam_s * sq)
        rep.step("λs (تأثير الحجم)", "λs = √(2/(1 + 0.004d)) ≤ 1", f"√(2/(1 + 0.004×{d:.0f}))", lam_s, "", LAMBDA_S)
        vc = rep.step("vc (Table 22.6.5.2)", "min[0.33λs√fc′ , (0.17 + 0.33/β)λs√fc′ , (0.17 + 0.083αs·d/bo)λs√fc′]",
                      f"min({vals[0]:.3f} , {vals[1]:.3f} , {vals[2]:.3f})", min(vals), "MPa", PUNCH_RC)
    rep.check("vu ≤ φvc (φ = 0.75)", vu, 0.75 * vc, "MPa", PHI)
    rep.results = {"vu_MPa": round(vu, 3), "phi_vc_MPa": round(0.75 * vc, 3), "ratio": round(vu / (0.75 * vc), 2)}
    return rep
