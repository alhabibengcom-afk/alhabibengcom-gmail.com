"""Stairs and bar bending schedule (BBS) for building_design.py.

Stairs are rarely in the ETABS model, so they come from a JSON list (--stairs stairs.json):
  [{"name": "ST1", "story": "Story1", "span": 3.6, "riser": 160, "going": 300, "t": 160, "width": 1.2,
    "landing": 1.4, "kind": "longitudinal", "support": "simple", "finishes": 1.5, "wL": 3.0, "count": 2}]
  span = horizontal projection of the flight (m); landing = landing length at the top (m, optional);
  kind = longitudinal | cantilever; count = number of identical flights in the building.

BBS rules (stated on the schedule; verify against ECP 203 detailing and the project specification):
  * anchorage/lap length = Ld from ecp203.footing.development_length (x --lap-factor, default 1.0)
  * standard hook / bend leg = 12 Ø (main bars), stirrup/tie hooks = 10 Ø each end (135°)
  * cut length = sum of the straight segments (no bend deduction) - conservative for ordering
  * unit weight = Ø² / 162 kg/m
"""
import math
import re
from collections import OrderedDict, defaultdict

HOOK = 12      # x dia, main bar bend leg
TIE_HOOK = 10  # x dia, each end of a tie/stirrup


def kg_m(d):
    return d * d / 162.0


def per_m(s):
    m = re.search(r"(\d+)\s*Ø\s*(\d+)\s*/\s*m", s or "")
    if not m:
        return None, None
    n, d = int(m.group(1)), int(m.group(2))
    return d, math.floor(1000 / n / 5) * 5  # dia, spacing (rounded down like the drawings)


def n_dia(s):
    m = re.search(r"(\d+)\s*Ø\s*(\d+)", s or "")
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)


def tie(s):
    m = re.search(r"Ø\s*(\d+)\s*@\s*(\d+)", s or "")
    return (int(m.group(1)), int(m.group(2))) if m else (8, 200)


def count(length, spacing):
    return int(math.floor(length / spacing)) + 1 if spacing else 0


# ---------------------------------------------------------------- stairs
def design_stairs(items, a, design_stair, design_one_way_slab, reports, skipped):
    out = []
    for s in items:
        kind = s.get("kind", "longitudinal")
        rep = design_stair(s["span"], s["riser"], s["going"], s["t"], s.get("finishes", 1.5), s.get("wL", 3.0), kind,
                           s.get("support", "simple"), s.get("width", 1.2), fcu=a.fcu, fy=a.fy_slab,
                           title=f"Stair {s.get('name', '')} - {s.get('story', '')}")
        reports.append(("stairs", rep))
        R = rep.results
        # distribution steel: minimum for a slab of the same thickness (ecp203 one-way slab rule)
        dist = design_one_way_slab(max(s["span"], 1.0), 1.0, 1.0, t=s["t"], fcu=a.fcu, fy=a.fy_slab).results.get(
            "distribution", "")
        out.append({**s, "kind": kind, "main": R.get("main_bottom") or R.get("top_per_m", ""), "top": R.get("top", ""),
                    "dist": dist, "wu": R.get("wu_kN_m2"), "ok": rep.ok,
                    "fail": [c.desc for c in rep.checks if not c.ok], "notes": rep.notes})
    return out


def draw_stairs(Sheet, template, stairs, a, short):
    for N in (20, 25, 30, 40, 50):
        S = Sheet(template, N)
        x = 0
        for st in stairs:
            R, G, t = st["riser"], st["going"], st["t"]
            span = st["span"] * 1000
            nst = max(1, round(span / G))
            rise = nst * R
            land = st.get("landing", 0) * 1000
            th = math.atan(R / G)
            tv = t / math.cos(th)  # vertical thickness of waist
            S.text(f"{st.get('name', 'ST')} - {st.get('story', '')}  SECTION", x + (span + land) / 2,
                   rise + S.th(18), 3.5, "ST-TEXT", "CENTER")
            if st["kind"] == "longitudinal":
                # step profile
                pts = [(x, 0)]
                for k in range(nst):
                    pts += [(x + k * G, (k + 1) * R), (x + (k + 1) * G, (k + 1) * R)]
                pts += [(x + span + land, rise)]
                S.msp.add_lwpolyline(pts, dxfattribs={"layer": "ST-SLAB"})
                # soffit: waist then landing
                S.msp.add_lwpolyline([(x, -tv), (x + span, rise - tv), (x + span + land, rise - tv),
                                      (x + span + land, rise)], dxfattribs={"layer": "ST-SLAB"})
                S.line((x, -tv), (x, 0), "ST-SLAB")
                c = 20 + 5
                tn = math.tan(th)
                # flight bottom bar: along the soffit, straight past the knee until it reaches the landing top
                # cover, then horizontal (anchorage in the landing)
                ext = max((tv - 2 * c) / tn, 0)
                kx = x + span + ext
                S.msp.add_lwpolyline([(x + 50, 50 * tn - tv + c), (kx, rise - c),
                                      (min(kx + 300, x + span + land - 50) if land else kx, rise - c)],
                                     dxfattribs={"layer": "ST-RFT"})
                if land:
                    # landing bottom bar: crosses the knee and continues into the waist
                    back = min(400, (tv - 2 * c) / tn)
                    S.msp.add_lwpolyline([(x + span - back, rise - tv + c), (x + span + land - 50, rise - tv + c),
                                          (x + span + land - 50, rise - c)], dxfattribs={"layer": "ST-RFT"})
                L4 = span / 4
                # top starters: bottom end along the waist top (hooked down), top end following the waist top
                # round the knee into the landing
                S.msp.add_lwpolyline([(x + 50, -tv + 2 * c), (x + 50, 50 * tn - c), (x + L4, L4 * tn - c)],
                                     dxfattribs={"layer": "ST-RFT"})
                S.msp.add_lwpolyline([(x + span - L4, rise - L4 * tn - c), (x + span, rise - c),
                                      (x + span + (min(land, L4) if land else 0), rise - c)],
                                     dxfattribs={"layer": "ST-RFT"})
                # distribution bars as dots along the soffit
                dd, sp = per_m(st["dist"])
                if sp:
                    k = 1
                    while k * sp < span:
                        px = x + k * sp
                        S.circle((px, px * 0 + (k * sp) * math.tan(th) - tv + c + 10), 5, "ST-RFT")
                        k += 1
                S.text(f"Main bot. {short(st['main'])}", x + span * 0.35, span * 0.35 * math.tan(th) - tv - S.th(6),
                       2.5, "ST-TEXT")
                S.text(f"Dist. {short(st['dist'])}", x + span * 0.35, span * 0.35 * math.tan(th) - tv - S.th(11),
                       2.5, "ST-TEXT")
                S.text(f"Top {short(st['top']) if st['top'] else short(st['dist'])} L/4 each end",
                       x + S.th(2), S.th(10), 2.5, "ST-TEXT")
                S.dim((x, -tv), (x + span, -tv), -S.th(18))
                if land:
                    S.dim((x + span, rise - tv), (x + span + land, rise - tv), -S.th(10))
                S.dim((x + span + land, 0), (x + span + land, rise), S.th(6))
                S.text(f"{nst} x {R}/{G}, waist t = {t}", x + span / 2, -tv - S.th(26), 2.5, "ST-TEXT", "CENTER")
                x += span + land + S.th(60)
            else:
                # cantilever steps: cross-section of one step across the width
                w = st["span"] * 1000
                S.rect(x - 250, -300, 250, rise + 600, "ST-WALL")
                S.msp.add_lwpolyline([(x, 0), (x + w, 0), (x + w, R), (x, R)], close=True,
                                     dxfattribs={"layer": "ST-SLAB"})
                S.msp.add_lwpolyline([(x - 200, R - 25 - 12 * 10), (x - 200, R - 25), (x + w - 25, R - 25)],
                                     dxfattribs={"layer": "ST-RFT"})
                S.text(f"Top {short(st['main'])} per m (min. 1 bar per step)", x, R + S.th(6), 2.5, "ST-TEXT")
                S.dim((x, 0), (x + w, 0), -S.th(8))
                S.text("Supporting beam/wall: design for torsion", x, -S.th(18), 2.5, "ST-TEXT")
                x += w + S.th(60)
        rows = [[st.get("name", ""), st.get("story", ""), st["kind"], f"{st['span']}", f"{st['riser']}/{st['going']}",
                 str(st["t"]), short(st["main"]), short(st["dist"]) if st["kind"] == "longitudinal" else "-",
                 short(st["top"]) if st["top"] else "-", "OK" if st["ok"] else "CHECK"] for st in stairs]
        yb = S.table(0, -S.th(45), ["Stair", "Story", "Type", "Span m", "R/G mm", "t mm", "Main", "Dist.", "Top",
                                    "ECP 203"], rows,
                     [S.th(12), S.th(16), S.th(22), S.th(14), S.th(18), S.th(10), S.th(18), S.th(18), S.th(18), S.th(16)])
        notes = [f"fcu = {a.fcu} N/mm2, fy = {a.fy_slab} N/mm2, cover 20 mm.",
                 "At the re-entrant (knee) corner bottom bars cross and continue by Ld - never bend them around the corner.",
                 "Top starter bars L/4 at both ends (partial fixity), distribution bars inside the main bars.",
                 "Designed as one-way slab on the horizontal projection (ECP 203 slab clauses)."]
        for k, n in enumerate(notes):
            S.text(f"{k + 1}. {n}", 0, yb - S.th(6) - k * S.th(5), 2.5, "ST-TEXT")
        if S.fits():
            break
    return S, N


# ---------------------------------------------------------------- BBS
class BBS:
    def __init__(self, Ld):
        self.rows = []
        self.Ld = Ld  # function dia -> mm
        self.mark = defaultdict(int)

    def add(self, element, member, members, desc, shape, dims, dia, n):
        """dims: list of segment lengths (mm). members: number of identical members."""
        if not dia or n <= 0 or members <= 0:
            return
        L = sum(dims)
        pre = {"Footing": "F", "Column": "C", "Beam": "B", "Slab": "S", "Wall": "W", "Stair": "ST"}[element]
        self.mark[pre] += 1
        tot_n = n * members
        tot_L = tot_n * L / 1000
        self.rows.append(OrderedDict([("Mark", f"{pre}{self.mark[pre]:02d}"), ("Element", element), ("Member", member),
                                      ("Description", desc), ("Shape", shape),
                                      ("Dims (mm)", " + ".join(str(round(v)) for v in dims)), ("Dia", dia),
                                      ("No./member", n), ("Members", members), ("Total No.", tot_n),
                                      ("Cut length (m)", round(L / 1000, 3)), ("Total length (m)", round(tot_L, 2)),
                                      ("Weight (kg)", round(tot_L * kg_m(dia), 1))]))


def build_bbs(res, ftypes, ctypes, btypes, ptypes, wtypes, stairs, a, Ld_fn):
    lapf = a.lap_factor

    def Ld(d, fcu):
        return math.ceil(Ld_fn(a.fy, fcu, d)[0] * lapf / 10) * 10

    B = BBS(Ld)
    M = res["model"]
    # footings (per type)
    for name, lst in ftypes:
        f = lst[0]
        c = 75
        for desc, along, across, s in (("bottom // L", f["Lf"], f["B"], f["bars_L"]), ("bottom // B", f["B"], f["Lf"], f["bars_B"])):
            d, sp = per_m(s)
            if not d:
                continue
            leg = HOOK * d
            straight = along - 2 * c
            B.add("Footing", name, len(lst), desc, "U (90° legs)", [leg, straight, leg], d, count(across - 2 * c, sp))
        # column starters in the footing are counted with the columns
    # columns: per label, per story
    stories = [s["name"] for s in M.stories]
    base = stories[-1] if stories else None
    by_label = defaultdict(list)
    for col in res["columns"]:
        by_label[col["label"]].append(col)
    groups = defaultdict(int)
    for lab, cs in by_label.items():
        cs.sort(key=lambda c: c["elev"] or 0)
        for k, col in enumerate(cs):
            n, d = n_dia(col["long"])
            H = M.height(col["story"]) * 1000
            first = M.story_below(col["story"]) == base
            last = k == len(cs) - 1
            dims = []
            shape = "straight"
            if first:
                cx_, cy_ = col.get("x"), col.get("y")
                fh = next((f["h"] for f in res["footings"] if cx_ is not None and cy_ is not None
                           and abs(f["x"] - cx_) < 0.01 and abs(f["y"] - cy_) < 0.01), None)
                if fh is None:
                    fh = 500
                    B_note = f"{lab}: no footing found under the column - anchorage assumes a 500 mm footing"
                    if B_note not in res["skipped"]:
                        res["skipped"].append(B_note)
                dims += [HOOK * d, fh - 75 - 25]
                shape = "L (into footing)"
            dims.append(H)
            if not last:
                dims.append(Ld(d, a.fcu))  # lap above the floor
            else:
                dims.append(HOOK * d)
                shape = "L top" if shape == "straight" else "U"
            key = (col["type"], col["story"], first, last, tuple(round(x) for x in dims), d)
            groups[key] += 1
    for (typ, st, first, last, dims, d), cnt in sorted(groups.items()):
        nb, _ = n_dia(next(c["long"] for c in res["columns"] if c["type"] == typ))
        shape = "L (into footing)" if first else ("L top" if last else "straight + lap")
        B.add("Column", f"{typ} @ {st}", cnt, "main bars", shape, list(dims), d, nb)
    tgroups = defaultdict(int)
    for col in res["columns"]:
        dt, s = tie(col["ties"])
        H = M.height(col["story"]) * 1000
        per = 2 * (col["b"] - 50) + 2 * (col["t"] - 50)
        tgroups[(col["type"], col["story"], dt, s, per, H)] += 1
    for (typ, st, dt, s, per, H), cnt in sorted(tgroups.items()):
        c_ = next(c for c in res["columns"] if c["type"] == typ)
        B.add("Column", f"{typ} @ {st}", cnt, "ties (closed, 135° hooks)", "rect. tie",
              [c_["b"] - 50, c_["t"] - 50, c_["b"] - 50, c_["t"] - 50, 2 * TIE_HOOK * dt], dt, count(H, s))
    # beams: per label/story (each has its own length)
    for bm in res["beams"]:
        Lb = (bm.get("L") or 0) * 1000
        if not Lb:
            continue
        c = 25
        nb, db = n_dia(bm["bot"])
        nt, dtp = n_dia(bm["top"])
        st_dia = int(re.search(r"Ø\s*(\d+)", bm["stir"]).group(1)) if re.search(r"Ø\s*(\d+)", bm["stir"] or "") else 8
        st_s = int(re.search(r"@\s*(\d+)", bm["stir"]).group(1)) if re.search(r"@\s*(\d+)", bm["stir"] or "") else 200
        legs = int(re.search(r"(\d+)\s*فرع", bm["stir"]).group(1)) if re.search(r"(\d+)\s*فرع", bm["stir"] or "") else 2
        mem = f"{bm['label']} @ {bm['story']} ({bm['type']})"
        B.add("Beam", mem, 1, "bottom (span)", "U (12d legs)", [HOOK * db, Lb - 2 * c, HOOK * db], db, nb)
        B.add("Beam", mem, 1, "top (supports), full length", "U (12d legs)", [HOOK * dtp, Lb - 2 * c, HOOK * dtp], dtp,
              max(nt, 2))
        B.add("Beam", mem, 1, f"stirrups {legs} legs", "rect. stirrup",
              [bm["b"] - 2 * c, bm["h"] - 2 * c, bm["b"] - 2 * c, bm["h"] - 2 * c, 2 * TIE_HOOK * st_dia], st_dia,
              count(Lb, st_s) * max(1, legs // 2))
    # slabs: per panel
    for q in res["slabs"]["panels"]:
        Lx, Ly = (q["x1"] - q["x0"]) * 1000, (q["y1"] - q["y0"]) * 1000
        mem = f"{q['type']} @ {q['story']} ({q['x0']:g},{q['y0']:g})"
        for desc, along, across, s in (("bottom X", Lx, Ly, q["bx"]), ("bottom Y", Ly, Lx, q["by"])):
            d, sp = per_m(s)
            if d:
                B.add("Slab", mem, 1, desc, "straight (to support c.l.)", [along + 2 * 6 * d], d, count(across - 100, sp))
        for edge, s, span, across in (("R", q["tx"], Lx, Ly), ("T", q["ty"], Ly, Lx)):
            if not q["cont"][edge]:
                continue
            d, sp = per_m(s)
            if d:
                leg = q["t"] - 2 * 20
                B.add("Slab", mem, 1, f"top over {'right' if edge == 'R' else 'top'} support (L/4 each side)",
                      "chair (bent legs)", [leg, span / 2, leg], d, count(across - 100, sp))
    # walls: per pier/story
    for w in res["walls"]:
        L = w["L"] * 1000
        H = w["H"] * 1000
        dv, sv = per_m(w["vert"])
        dh, sh = per_m(w["hor"])
        mem = f"{w['pier']} @ {w['story']} ({w['type']})"
        if dv:
            B.add("Wall", mem, 1, "vertical, 2 faces", "straight + lap", [H + 200, Ld(dv, a.fcu)], dv, 2 * count(L - 50, sv))
        if dh:
            B.add("Wall", mem, 1, "horizontal, 2 faces", "U (12d legs)", [HOOK * dh, L - 50, HOOK * dh], dh,
                  2 * count(H, sh))
    # stairs
    for st in stairs:
        if st["kind"] != "longitudinal":
            d, sp = per_m(st["main"])
            if d:
                B.add("Stair", st.get("name", ""), st.get("count", 1), "top per step (cantilever)", "L (anchored)",
                      [Ld(d, a.fcu), st["span"] * 1000 - 25], d, count(st.get("width", 1.2) * 1000, sp))
            continue
        th = math.atan(st["riser"] / st["going"])
        Lin = st["span"] * 1000 / math.cos(th)
        land = st.get("landing", 0) * 1000
        W = st.get("width", 1.2) * 1000
        d, sp = per_m(st["main"])
        if d:
            B.add("Stair", st.get("name", ""), st.get("count", 1), "main bottom, flight", "straight",
                  [Lin + Ld(d, a.fcu)], d, count(W - 50, sp))
            if land:
                B.add("Stair", st.get("name", ""), st.get("count", 1), "main bottom, landing (crosses at knee)",
                      "L", [Ld(d, a.fcu) + land - 25, HOOK * d], d, count(W - 50, sp))
        d2, sp2 = per_m(st["top"] or st["dist"])
        if d2:
            B.add("Stair", st.get("name", ""), st.get("count", 1), "top starters L/4, both ends", "L",
                  [Lin / 4 + Ld(d2, a.fcu), HOOK * d2], d2, 2 * count(W - 50, sp2))
        d3, sp3 = per_m(st["dist"])
        if d3:
            B.add("Stair", st.get("name", ""), st.get("count", 1), "distribution", "straight", [W - 50], d3,
                  count(Lin + land, sp3))
    return B


def bbs_summary(B):
    by_d = defaultdict(lambda: [0.0, 0.0])
    by_el = defaultdict(float)
    for r in B.rows:
        by_d[r["Dia"]][0] += r["Total length (m)"]
        by_d[r["Dia"]][1] += r["Weight (kg)"]
        by_el[r["Element"]] += r["Weight (kg)"]
    return by_d, by_el


def write_bbs_xlsx(B, wb, a):
    from openpyxl.styles import Font, Alignment
    ws = wb.create_sheet("BBS")
    hdr = list(B.rows[0].keys()) if B.rows else []
    ws.append(hdr)
    for r in B.rows:
        ws.append(list(r.values()))
    by_d, by_el = bbs_summary(B)
    ws2 = wb.create_sheet("Steel summary")
    ws2.append(["Diameter (mm)", "kg/m", "Total length (m)", "Weight (kg)", "Weight (t)"])
    tot = 0.0
    for d in sorted(by_d):
        ws2.append([d, round(kg_m(d), 3), round(by_d[d][0], 1), round(by_d[d][1], 1), round(by_d[d][1] / 1000, 3)])
        tot += by_d[d][1]
    ws2.append(["TOTAL", "", "", round(tot, 1), round(tot / 1000, 3)])
    ws2.append([])
    ws2.append(["Element", "Weight (kg)", "Weight (t)"])
    for el, w in by_el.items():
        ws2.append([el, round(w, 1), round(w / 1000, 3)])
    ws2.append([])
    for n in bbs_notes(a):
        ws2.append([n])
    for w in (ws, ws2):
        for c in w[1]:
            c.font = Font(bold=True)
        for col in w.columns:
            w.column_dimensions[col[0].column_letter].width = max(9, min(42, max(len(str(c.value or "")) for c in col) + 2))
    return tot


def bbs_notes(a):
    return [f"Laps/anchorage = Ld from ecp203 development_length x {a.lap_factor} (fy {a.fy}, fcu {a.fcu}) - verify "
            "against ECP 203 splice clauses.",
            f"Main-bar bend legs = {HOOK} dia; ties/stirrups: 135° hooks {TIE_HOOK} dia each end.",
            "Cut lengths are the sum of segments without bend deduction (slightly conservative for ordering).",
            "Beam top bars taken full length (conservative); curtail per the detailing drawing if required.",
            "Column extra cross-ties for intermediate bars, slab edge U-bars, trimmer bars at openings and waste "
            "are not included - add a wastage allowance per the specification.",
            "Flat-slab strips are not scheduled (bar lengths depend on the strip layout) - schedule from the "
            "flat-slab sheet."]


def draw_bbs(Sheet, template, B, a, title_fields, out_path_fn):
    """One or more A1 sheets with the BBS table and a diameter summary. Returns list of (path, N)."""
    sheets = []
    rows = B.rows
    per_sheet = 45
    pages = [rows[i:i + per_sheet] for i in range(0, len(rows), per_sheet)] or [[]]
    by_d, by_el = bbs_summary(B)
    for pg, chunk in enumerate(pages):
        N = 100
        S = Sheet(template, N)
        S.text("BAR BENDING SCHEDULE" + (f" ({pg + 1}/{len(pages)})" if len(pages) > 1 else ""), 0, S.th(8), 5,
               "ST-TEXT")
        data = [[r["Mark"], r["Element"], str(r["Member"])[:30], str(r["Description"])[:34], r["Shape"].replace("Ø", "d"),
                 r["Dims (mm)"][:30], f"T{r['Dia']}", str(r["No./member"]), str(r["Members"]), str(r["Total No."]),
                 f"{r['Cut length (m)']:.2f}", f"{r['Total length (m)']:.1f}", f"{r['Weight (kg)']:.1f}"] for r in chunk]
        widths = [S.th(10), S.th(14), S.th(48), S.th(52), S.th(40), S.th(44), S.th(9), S.th(14), S.th(13), S.th(13),
                  S.th(16), S.th(17), S.th(16)]
        yb = S.table(0, 0, ["Mark", "Element", "Member", "Description", "Shape", "Segments (mm)", "Dia", "No./mem.",
                            "Members", "Total", "Cut L (m)", "Total L (m)", "kg"], data, widths, h=2.0)
        if pg == len(pages) - 1:
            sx = sum(widths) + S.th(15)
            srows = [[f"T{d}", f"{kg_m(d):.3f}", f"{by_d[d][0]:.1f}", f"{by_d[d][1]:.1f}"] for d in sorted(by_d)]
            tot = sum(v[1] for v in by_d.values())
            srows.append(["TOTAL", "", "", f"{tot:.1f}"])
            S.text("STEEL SUMMARY", sx, S.th(8), 4, "ST-TEXT")
            y2 = S.table(sx, 0, ["Dia", "kg/m", "Length m", "Weight kg"], srows,
                         [S.th(12), S.th(14), S.th(18), S.th(18)], h=2.0)
            erows = [[el, f"{w:.1f}", f"{w / 1000:.3f}"] for el, w in by_el.items()]
            y3 = S.table(sx, y2 - S.th(8), ["Element", "kg", "t"], erows, [S.th(16), S.th(18), S.th(14)], h=2.0)
            for k, n in enumerate(bbs_notes(a)):
                S.text(f"{k + 1}. {n}", 0, yb - S.th(6) - k * S.th(4.5), 2.0, "ST-TEXT")
        num = str(504 + pg)
        path = out_path_fn(num)
        S.finish(path, title_fields("BAR BENDING SCHEDULE", num, N, "ZZ"))
        sheets.append((path, N))
    return sheets
