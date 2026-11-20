"""تصميم سقف بوست تنشن كامل (فلات سلاب، كابلات غير مترابطة) — ACI 318-19.

الخطوات:
1. تحليل إطار مكافئ في كل اتجاه بجساءة غير منشورية (R8.4.1.2 بيشترط EFM أو تحليل عددي، ومش مسموح بالمعاملات المبسطة).
2. توزيع الكابلات بطريقة موازنة الأحمال (Load balancing): قطع مكافئ، أعلى نقطة فوق الأعمدة وأوطى نقطة في منتصف البحر،
   وعند المراسي الطرفية على محور القطاع. القوة بتتحدد علشان توازن نسبة من الوزن الذاتي، ومش أقل من fpc = 0.9 MPa.
3. العزوم الثانوية M2 = Mbal − P·e من تحليل الإطار تحت الأحمال المكافئة للكابلات.
4. مراجعة كل قطاع حرج بـ check_pt_section (عرض الإطار كامل)، والقص الثاقب بـ check_pt_punching لكل عمود.

حدود: شبكة منتظمة، من غير بلاطات سقوط ولا فتحات كبيرة. كابلات موزعة على عرض الإطار في الاتجاهين — في التنفيذ عادةً
بتتجمع (Banded) في اتجاه وتتوزع في الاتجاه التاني، والقوة الكلية لكل إطار هي اللي بتهم في المراجعة دي.
"""
from __future__ import annotations

import math
from itertools import product

from ecp203.grid import Grid
from ecp203.report import Report

from .pt_slab import LOAD, R, check_pt_punching, check_pt_section

EFM = R("6.2.4.1(b) (PDF page 110) و R8.4.1.2 (الإطار المكافئ للبلاطات سابقة الإجهاد، جساءة غير منشورية)", 166)
PATTERN = R("6.4.3.2 / 6.4.3.3 (ترتيب الحمل الحي: كامل لو L ≤ 0.75D، وإلا 75% بترتيبات)", 117)
FPC_MIN_REF = R("8.6.2.1 (fpc ≥ 0.9 MPa)", 181)
GAMMA = 25.0  # kN/m³ — كود الأحمال


def _ll_patterns(n, LL, D):
    if LL <= 0.75 * D:
        return [[1.0] * n], True
    pats = [[1.0] * n]
    if n <= 10:
        pats += [[0.75 * p for p in pat] for pat in product((0, 1), repeat=n)]
    else:
        alt = [k % 2 for k in range(n)]
        pats += [[0.75 * a for a in alt], [0.75 * (1 - a) for a in alt]]
        pats += [[0.75 if k in (s, s + 1) else 0 for k in range(n)] for s in range(n - 1)]
    return pats, False


def _profile(fr, h_m, cgs_top, cgs_bot):
    """e (m، موجبة لأسفل) عند الركائز ومنتصف البحور، وارتفاع القوس a لكل بحر."""
    n = len(fr.spans)
    e_sup = [0.0 if (k == 0 or k == n) else -(h_m / 2 - cgs_top) for k in range(n + 1)]
    e_mid = h_m / 2 - cgs_bot
    a = [e_mid - (e_sup[j] + e_sup[j + 1]) / 2 for j in range(n)]
    return e_sup, e_mid, a


def _e_at(fr, node, e_sup, a):
    xg = fr.x[node]
    for j, L in enumerate(fr.spans):
        x0 = fr._sup_x[j]
        if x0 - 1e-9 <= xg <= x0 + L + 1e-9:
            xi = (xg - x0) / L
            return e_sup[j] * (1 - xi) + e_sup[j + 1] * xi + 4 * a[j] * xi * (1 - xi)
    return 0.0


def design_pt_floor(x, y, h, SDL, LL, fc=35, fci=25, fy=420, col=(500, 500), col_override=None, H_below=3.2,
                    H_above=3.2, fpu=1860, strand_area=98.7, fse=1100, loss_long=0.15, balance=0.8, cgs_top=45,
                    cgs_bot=45, detail=False, title=None):
    """x, y محاور (m)، h (mm)، SDL و LL (kN/m²)، strand_area مساحة الإستراند الواحد (mm²)، fse الإجهاد الفعال بعد كل
    الفواقد (MPa)، loss_long نسبة الفواقد طويلة المدى (لحساب Pi)، balance نسبة الوزن الذاتي المطلوب موازنتها،
    cgs_top / cgs_bot بعد محور الكابل عن الوش العلوي/السفلي (mm). detail=True يرفق تقرير كل قطاع، وإلا الفاشلة بس."""
    g = Grid(list(x), list(y), h, tuple(col), col_override or {}, H_below, H_above)
    rep = Report(title or f"سقف بوست تنشن {len(x)}×{len(y)} محاور، سمك {h} مم — ACI 318-19")
    rep.inputs = {"محاور X (m)": ", ".join(f"{v:g}" for v in x), "محاور Y (m)": ", ".join(f"{v:g}" for v in y),
                  "h": f"{h} mm", "SDL / LL": f"{SDL} / {LL} kN/m²", "fc′ / fci′": f"{fc} / {fci} MPa",
                  "الإستراند": f"{strand_area} mm² ، fpu = {fpu} ، fse = {fse} MPa", "نسبة الموازنة": f"{balance*100:.0f}% من الوزن الذاتي",
                  "CGS علوي / سفلي": f"{cgs_top} / {cgs_bot} mm", "الأعمدة": f"{col[0]}×{col[1]} mm"}
    rep.note("fse و loss_long افتراضات: دخّل القيم من حسابات الفواقد الفعلية (احتكاك، انزلاق المرساة، انكماش، زحف، استرخاء).")
    h_m = h / 1000
    SW = rep.step("الوزن الذاتي", "γ·h", f"25×{h_m}", GAMMA * h_m, "kN/m²")
    D = SW + SDL
    pats_info = _ll_patterns(1, LL, D)[1]
    rep.step("ترتيب الحمل الحي", "L ≤ 0.75 D → الحمل الحي كامل على كل البواكي", f"L = {LL} ، 0.75D = {0.75*D:.2f}",
             "كامل على الكل" if pats_info else "كامل + ترتيبات 75%", "", PATTERN)
    qu = 1.2 * D + 1.6 * LL

    col_info = {}
    n_checked = [0]
    for direction in ("x", "y"):
        rep.step(f"— الإطارات في اتجاه {direction.upper()} —", "", "", "", "")
        for name, k, fr in g.frames(direction):
            n = len(fr.spans)
            l2 = fr.l2
            e_sup, e_mid, a = _profile(fr, h_m, cgs_top / 1000, cgs_bot / 1000)
            wsw = SW * l2
            P_bal = max(balance * wsw * L ** 2 / (8 * aj) for L, aj in zip(fr.spans, a))
            P_min = 0.9 * l2 * h  # kN
            P_need = max(P_bal, P_min)
            n_str = math.ceil(P_need * 1e3 / (strand_area * fse))
            Pe = n_str * strand_area * fse / 1e3
            Aps = n_str * strand_area
            wb = [8 * Pe * aj / L ** 2 for L, aj in zip(fr.spans, a)]
            bal_pct = [w / wsw * 100 for w in wb]
            rep.step(f"إطار {name}: قوة الشد والكابلات",
                     "P = max(β·wSW·L²/(8a) , 0.9 MPa·A) ← n = P/(Aps1·fse)",
                     f"P_bal = {P_bal:.0f} ، P_min = {P_min:.0f} kN ، عرض {l2:.2f} م",
                     f"{n_str} إستراند ، Pe = {Pe:.0f} kN ، موازنة {', '.join(f'{p:.0f}%' for p in bal_pct)}", "", FPC_MIN_REF)

            Mb, Rb, Mcb = fr.combine([-w for w in wb])
            Msw, Rsw, Mcsw = fr.combine([wsw] * n)
            Msdl, _, Mcsdl = fr.combine([SDL * l2] * n)
            pats, _ = _ll_patterns(n, LL, D)
            ll_res = [fr.combine([LL * l2 * p for p in pat]) for pat in pats]

            def sec(node, region, L, c2):
                e = _e_at(fr, node, e_sup, a)
                M2 = Mb[node] - (-Pe * e)
                ML = (min if region == "negative" else max)(r[0][node] for r in ll_res)
                return check_pt_section(b=l2 * 1000, h=h, fc=fc, fci=fci, Aps=Aps, Pe=Pe, Pi=Pe / (1 - loss_long),
                                        e=round(e * 1000, 1), M_D=float(Msw[node]), M_SDL=float(Msdl[node]),
                                        M_L=float(ML), M2=float(M2), M_sw=float(Msw[node]), region=region, span=L,
                                        fpu=fpu, fy=fy, frame_width=l2 * 1000, column_width=c2,
                                        title=f"إطار {name} — بحر {j+1} — {'وش ركيزة' if region == 'negative' else 'موجب'}")

            rows = []
            checked = []
            for j, L in enumerate(fr.spans):
                nL, nR = fr.face_nodes(j)
                inner = [kk for kk in fr.span_nodes(j) if fr.x[nL] <= fr.x[kk] <= fr.x[nR]]
                n_pos = max(inner, key=lambda kk: Msw[kk] + Msdl[kk] + max(r[0][kk] for r in ll_res))
                for node, region, sname, sup in ((nL, "negative", "يسار", j), (n_pos, "positive", "موجب", None),
                                                 (nR, "negative", "يمين", j + 1)):
                    c2 = fr.supports[sup].c2 * 1000 if sup is not None else None
                    ch = sec(node, region, L, c2)
                    ch.title = ch.title.replace("وش ركيزة", f"وش ركيزة {sname}")
                    checked.append(ch)
                    if detail or not ch.ok:
                        rep.children.append(ch)
                    r_ = ch.results
                    rows.append(f"بحر {j+1} {sname}: ftop/fbot = {r_['f_top/f_bot service (MPa)']} ، "
                                f"As = {r_['As_required_mm2']:.0f} mm² ، Mu/φMn = {r_['Mu_kNm']}/{r_['phiMn_kNm']} "
                                f"{'✓' if ch.ok else '✗'}")
            rep.step(f"إطار {name}: مراجعة القطاعات (تفاصيل كل قطاع في الملحق)", "check_pt_section", " ؛ ".join(rows),
                     "✓" if all(c.ok for c in checked) else "✗ راجع الملحق", "", EFM)
            for c in checked:
                if not c.ok:
                    rep.check(f"{c.title}", 1, 0, "", EFM)
            n_checked[0] += len(checked)

            # بيانات الأعمدة
            fpc = Pe / (l2 * h)  # MPa (kN / (m·mm) = MPa)
            _, Rsdl, _ = fr.combine([SDL * l2] * n)
            for m in range(n + 1):
                Rl = max(r[1][m] for r in ll_res)
                Vu = 1.2 * (Rsw[m] + Rsdl[m]) + 1.6 * Rl
                Mcu = max(abs(1.2 * (Mcsw[m] + Mcsdl[m]) + 1.6 * r[2][m] + Mcb[m]) for r in ll_res)
                i, j2 = (m, k) if direction == "x" else (k, m)
                d = col_info.setdefault((i, j2), {"Vu": 0.0, "Msc": 0.0, "fpc": []})
                d["Vu"] = max(d["Vu"], Vu)
                d["Msc"] = max(d["Msc"], Mcu)
                d["fpc"].append(fpc)

    # القص الثاقب
    rep.step("— القص الثاقب عند كل عمود —", "", "", "", "")
    d_eff = 0.8 * h
    for (i, j), d in sorted(col_info.items()):
        cx, cy = g.col_size(i, j)
        loc = g.location(i, j)
        A_in = (cx + d_eff) * (cy + d_eff) / 1e6
        Vu = d["Vu"] - qu * A_in
        fpc = sum(d["fpc"]) / len(d["fpc"])
        pr = check_pt_punching(cx, cy, h, Vu, fc, fpc=fpc, location=loc, Msc=d["Msc"] if loc == "interior" else 0.0)
        rep.check(f"قص ثاقب عمود ({i+1},{j+1}) {loc}: vu/φvc", pr.results["ratio"], 1.0, "", R("22.6.5.5 / 22.6.5.2", 645))
    rep.note("القص الثاقب: Vp (المركبة الرأسية للكابلات) اتهملت (متحفظ). وللأعمدة الطرفية والركنية نقل العزم مش داخل في "
             "الحساب: دخّل vu من البرنامج لو قريب من الحد.")
    rows = [f"({i+1},{j+1}): Vu = {d['Vu']:.0f} kN ، Msc = {d['Msc']:.0f} kN·m" for (i, j), d in sorted(col_info.items())]
    rep.step("أحمال الأعمدة من السقف (قصوى، 1.2D + 1.6L)", "", " ؛ ".join(rows), "", "", LOAD)
    rep.note("الترخيم (24.2) مش محسوب: موازنة 60–100% من الوزن الذاتي عادة بتتحكم فيه، لكن راجعه بالبرنامج.")
    rep.note("الأعمدة والقواعد بتتصمم بالكود المصري (قاعدة المكتب) بأحمال تشغيل D و L، مش بمعاملات ACI.")
    rep.results = {"h_mm": h, "sections_checked": n_checked[0],
                   "sections_failing": sum(1 for c in rep.children if not c.ok)}
    rep.note("تقارير القطاعات الفاشلة متلحقة تحت. لكل القطاعات شغّل بـ detail=true.")
    return rep
