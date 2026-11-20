"""تصميم سقف فلات سلاب كامل (غير سابق الإجهاد) - ECP 203-2020.

الخطوات:
1. الأحمال والسمك الأدنى وأبعاد الأعمدة الدنيا.
2. تحليل كل إطار مكافئ في الاتجاهين (الباب 6 صفحة 256) مع كل ترتيبات الحمل الحي.
3. توزيع العزوم على شريحة العمود وشريحة الوسط وتصميم التسليح لكل متر.
4. القص الثاقب عند كل عمود.
5. أحمال الأعمدة من السقف ده.

الشروط: شبكة محاور منتظمة (الأعمدة على خطوط مستقيمة متعامدة). أي شبكة غير منتظمة أو فتحات
كبيرة → حلل بـ SAFE وصمم الشرائح بـ design_slab_strip.
"""
from __future__ import annotations

from itertools import product

from . import params as P
from .grid import Grid
from .report import Report
from .slab import check_flat_slab_punching, strip_steel


def _patterns(n):
    if n <= 10:
        return [list(p) for p in product((0, 1), repeat=n)]
    alt1 = [(k % 2) for k in range(n)]
    return [[1] * n, alt1, [1 - a for a in alt1]] + [[1 if k in (s, s + 1) else 0 for k in range(n)] for s in range(n - 1)]


def envelope(frame, wD, wL, patterns):
    """wD و wL حمل خطي (kN/m) — بيرجع لكل بحر: (M_left_face_min, M_pos_max, M_right_face_min) وردود الأفعال القصوى."""
    nsp = len(frame.spans)
    out = []
    Rmax = None
    Mcmax = None
    for j in range(nsp):
        nL, nR = frame.face_nodes(j)
        inner = [k for k in frame.span_nodes(j) if frame.x[nL] <= frame.x[k] <= frame.x[nR]]
        mL = mR = 1e18
        mp = -1e18
        for pat in patterns:
            w = [wD + wL * p for p in pat]
            M, R, Mc = frame.combine(w)
            mL, mR = min(mL, M[nL]), min(mR, M[nR])
            mp = max(mp, max(M[k] for k in inner))
            if j == 0:
                Rmax = R if Rmax is None else [max(a, b) for a, b in zip(Rmax, R)]
                Mcmax = [abs(c) for c in Mc] if Mcmax is None else [max(a, abs(b)) for a, b in zip(Mcmax, Mc)]
        out.append((mL, mp, mR))
    return out, Rmax, Mcmax


def _strip_widths(frame, j):
    """عرض شريحة العمود = ربع البعد الأصغر للباكية على كل جانب (نص البعد الأصغر للإطار الداخلي)."""
    l1 = frame.spans[j]
    sides = frame.supports[j].l2_sides
    cs = sum(min(l1, s) / 4 for s in sides)
    return cs, max(frame.l2 - cs, 0.0)


def design_flat_slab_floor(x, y, h, SDL, LL, fcu=30, fy=400, col=(500, 500), col_override=None,
                           H_below=3.2, H_above=3.2, cover=20.0, title=None):
    """x, y: إحداثيات المحاور (m). h: سمك البلاطة (mm). SDL و LL بالـ kN/m². col: (cx, cy) mm."""
    g = Grid(list(x), list(y), h, tuple(col), col_override or {}, H_below, H_above)
    rep = Report(title or f"سقف فلات سلاب {len(x)}×{len(y)} محاور، سمك {h} مم — ECP 203-2020")
    rep.inputs = {"محاور X (m)": ", ".join(f"{v:g}" for v in x), "محاور Y (m)": ", ".join(f"{v:g}" for v in y),
                  "h": f"{h} mm", "SDL / LL": f"{SDL} / {LL} kN/m²", "fcu / fy": f"{fcu} / {fy}",
                  "الأعمدة": f"{col[0]}×{col[1]} mm" + (" (مع استثناءات)" if col_override else ""),
                  "ارتفاع الدور تحت / فوق": f"{H_below} / {H_above} m"}

    # ---------------- الأحمال والأبعاد
    rep.step("— الأحمال والأبعاد —", "", "", "", "")
    SW = rep.step("الوزن الذاتي", "γ·h", f"25×{h/1000}", P.GAMMA_RC * h / 1000, "kN/m²", P.REF_UNIT_WEIGHT)
    qD = SW + SDL
    qu = rep.step("الحمل الأقصى", "1.4(SW + SDL) + 1.6 LL", f"1.4×{qD:.2f} + 1.6×{LL}", P.LOAD_D * qD + P.LOAD_L * LL,
                  "kN/m²", P.REF_LOADS)
    if LL > 2 * qD:
        rep.note("الحمل الحي أكبر من ضعف الميت: راجع حدود الطريقة.")
    spans_x = [b - a for a, b in zip(x, x[1:])]
    spans_y = [b - a for a, b in zip(y, y[1:])]
    Lmax = max(spans_x + spans_y)
    ext = max(spans_x[0], spans_x[-1], spans_y[0], spans_y[-1])
    t_req = max(ext * 1000 / P.FS_T_MIN["exterior"], Lmax * 1000 / P.FS_T_MIN["interior"], P.FS_T_ABS)
    rep.step("أقل سمك للبلاطة", "max(Lext/30 , L/32 , 150)", f"max({ext*1000:.0f}/30 , {Lmax*1000:.0f}/32 , 150)", t_req,
             "mm", P.REF_FS_T)
    rep.check("h ≥ hmin", h, t_req, "mm", P.REF_FS_T, "≥")
    H = max(v for v in (H_below, H_above) if v)
    sizes = {g.col_size(i, j) for i, j in g.columns()}
    for cx, cy in sizes:
        need = max(Lmax * 1000 / P.FS_COL_MIN[0], H * 1000 / P.FS_COL_MIN[1], P.FS_COL_MIN[2])
        rep.check(f"أقل بعد للعمود {cx}×{cy}", min(cx, cy), need, "mm", P.REF_FS_COL, "≥")

    # ---------------- الإطارات
    col_loads = {}
    for direction in ("x", "y"):
        layer_cover = cover if direction == "x" else cover + 12
        rep.step(f"— الإطارات في اتجاه {direction.upper()} —", "", "", "", "")
        for name, k, fr in g.frames(direction):
            pats = _patterns(len(fr.spans))
            env, Rmax, Mcmax = envelope(fr, P.LOAD_D * qD * fr.l2, P.LOAD_L * LL * fr.l2, pats)
            rows = []
            for j, (mL, mp, mR) in enumerate(env):
                cs, ms = _strip_widths(fr, j)
                for sec, M, kind in (("وش يسار", mL, "neg"), ("موجب", mp, "pos"), ("وش يمين", mR, "neg")):
                    if kind == "neg" and M >= 0:
                        continue
                    pct = P.FS_STRIP_PCT[kind]
                    tmp = Report("tmp")
                    m_cs = abs(M) * pct / cs if cs else 0
                    m_ms = abs(M) * (1 - pct) / ms if ms else 0
                    a = strip_steel(m_cs, h, fcu, fy, tmp, "", layer_cover)
                    b = strip_steel(m_ms, h, fcu, fy, tmp, "", layer_cover) if ms else None
                    if not tmp.ok or a is None:
                        rep.check(f"{name} بحر {j+1} {sec}: القطاع كافي للعزم", 1, 0, "", P.REF_CMAX)
                    pos = "سفلي" if kind == "pos" else "علوي"
                    rows.append(f"بحر {j+1} {sec} ({pos}): M = {M:.0f} kN·m → شريحة عمود {a and a['bars']} | "
                                f"شريحة وسط {b and b['bars']}")
            rep.step(f"إطار {name} (عرض {fr.l2:.2f} م، بحور {', '.join(f'{s:g}' for s in fr.spans)} م)",
                     "تحليل إطار مكافئ + كل ترتيبات الحمل الحي ← توزيع الشرائح (عمود/وسط)",
                     " ؛ ".join(rows), "", "", P.REF_FS_EFM)
            for m, R in enumerate(Rmax):
                i, j2 = (m, k) if direction == "x" else (k, m)
                d = col_loads.setdefault((i, j2), {"Pu": 0.0, "Mx": 0.0, "My": 0.0})
                if direction == "x":
                    d["Pu"] = max(d["Pu"], R)
                    d["Mx"] = Mcmax[m]
                else:
                    d["Pu"] = max(d["Pu"], R)
                    d["My"] = Mcmax[m]
    rep.note(f"توزيع العزوم على الشرائح: {P.FS_STRIP_PCT['neg']*100:.0f}% سالب و{P.FS_STRIP_PCT['pos']*100:.0f}% موجب "
             f"لشريحة العمود ({P.REF_FS_STRIPS}).")
    rep.note(f"معاملات الأعمدة المكافئة: {P.REF_FS_KEC}.")
    rep.note("عزم العمود المنقول (Mx / My) هو المجموع للعمود العلوي والسفلي؛ بيتوزع بينهم بنسبة جساءتهم.")

    # ---------------- القص الثاقب
    rep.step("— القص الثاقب عند كل عمود —", "", "", "", "")
    d_avg = h - cover - 12
    worst = 0
    for (i, j), d in sorted(col_loads.items()):
        cx, cy = g.col_size(i, j)
        loc = g.location(i, j)
        A_in = (cx + d_avg) * (cy + d_avg) / 1e6
        Vu = d["Pu"] - qu * A_in
        pr = check_flat_slab_punching(cx, cy, h, Vu, fcu, loc, cover)
        ratio = pr.results["ratio"]
        worst = max(worst, ratio)
        rep.check(f"قص ثاقب عمود ({i+1},{j+1}) {loc}: qup/qcup", ratio, 1.0, "", P.REF_PUNCH)
    rep.note("القص الثاقب للأعمدة الطرفية والركنية بمعامل β تقريبي لتأثير العزوم المنقولة؛ لو قريب من الحد احسبه بدقة.")

    # ---------------- أحمال الأعمدة
    rows = [f"({i+1},{j+1}): Pu = {d['Pu']:.0f} kN ، Mx = {d['Mx']:.0f} ، My = {d['My']:.0f} kN·m"
            for (i, j), d in sorted(col_loads.items())]
    rep.step("أحمال الأعمدة من السقف ده (قصوى)", "Pu = رد فعل الإطار ، M = العزم المنقول للعمود المكافئ", " ؛ ".join(rows),
             "", "", P.REF_FS_EFM)
    rep.results = {"h_mm": h, "qu_kN_m2": round(qu, 2), "max_punching_ratio": round(worst, 2)}
    rep.note("الترخيم والتشرخ مش محسوبين؛ والفتحات والأحمال المركزة مش متغطية.")
    return rep
