#!/usr/bin/env python3
"""Design a building from its ETABS exports with the office ECP 203 library and draw the structural sheets.

  python3 building_design.py --model m.e2k --reactions reactions.xlsx --forces forces.xlsx \
      --combos U1,U2 --q-allow 200 --project-code PRJ --project "Project name" -o out/

Steps
  1. Read the model (.e2k) and the exported tables (model_reader.py).
  2. Design every footing (isolated), column (per story) and beam (per story) with Egyptian codes/ecp203.
  3. Group identical results into types F1.., C1.., B1.. (largest first).
  4. Write: design.xlsx (all elements + types), reports/*.md (full ECP 203 calculations),
     DXF sheets on the Al-Habeeb template (mm, origin at grid A/1, ST-/GN- layers, title block):
        <code>-ST-ZZ-101_R00.dxf  foundation plan + footing schedule + footing details
        <code>-ST-ZZ-501_R00.dxf  column schedule + column sections
        <code>-ST-ZZ-502_R00.dxf  beam schedule + beam sections
     and PNG previews of each sheet.

Drawings are design drafts generated from the analysis: an engineer must review, complete (slabs, walls, stairs,
development lengths, laps, notes) and sign them before issue.
"""
import argparse
import json
import math
import os
import re
import sys
from collections import OrderedDict, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import model_reader as MR  # noqa: E402
import slabs_walls as SW  # noqa: E402


def find_lib(start):
    for base in (start, os.getcwd(), os.path.join(HERE, "..", "..", ".."), os.path.join(HERE, "..", "..", "..", "..")):
        p = os.path.abspath(os.path.join(base, "Egyptian codes"))
        if os.path.isdir(os.path.join(p, "ecp203")):
            return p
    return None


def find_template():
    import glob
    c = glob.glob("/root/.claude/skills/**/alhabeeb-cad-standards/assets/AH-template.dxf", recursive=True)
    c += glob.glob(os.path.expanduser("~/.claude/skills/**/alhabeeb-cad-standards/assets/AH-template.dxf"), recursive=True)
    return c[0] if c else None


# ---------------------------------------------------------------- bar text parsing
def bars_per_m(s):
    m = re.search(r"(\d+)\s*Ø\s*(\d+)\s*/\s*m", s or "")
    return (int(m.group(1)), int(m.group(2))) if m else (None, None)


def bars_n(s):
    m = re.search(r"(\d+)\s*Ø\s*(\d+)", s or "")
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)


def ties(s):
    m = re.search(r"Ø\s*(\d+)\s*@\s*(\d+)", s or "")
    return (int(m.group(1)), int(m.group(2))) if m else (8, 200)


def short(s):
    """'5Ø12 (565 mm², 1 صف)' -> '5T12'; '8Ø12/m (...)' -> 'T12@125'; ties -> 'T8@200'"""
    if not s:
        return "-"
    n, d = bars_per_m(s)
    if n:
        return f"T{d}@{math.floor(1000 / n / 5) * 5:.0f}"  # round spacing DOWN (never less steel)
    m = re.search(r"(\d+)\s*فرع\s*Ø\s*(\d+)\s*@\s*(\d+)", s)
    if m:
        return f"{m.group(1)}L T{m.group(2)}@{m.group(3)}"
    m = re.search(r"^\s*Ø\s*(\d+)\s*@\s*(\d+)", s)
    if m:
        return f"T{m.group(1)}@{m.group(2)}"
    n, d = bars_n(s)
    return f"{n}T{d}" if n else s


# ---------------------------------------------------------------- design
def design_all(a, lib):
    sys.path.insert(0, lib)
    from ecp203.footing import design_isolated_footing
    from ecp203.column import design_column
    from ecp203.beam import design_beam

    M = MR.read_e2k(a.model)
    res = {"model": M, "footings": [], "columns": [], "beams": [], "skipped": []}
    reports = []

    # ---- footings from reactions
    if a.reactions:
        T = MR.read_any_tables(a.reactions)
        _, t = MR.find_table(T, "reaction")
        t = t or next(iter(T.values()))
        Dset, Lset = MR.case_groups(M, a.dead_cases, a.live_cases)
        fz = next((c for c in t["records"][0] if MR.norm(c) in ("fz", "f3")), None) if t["records"] else None
        ff = MR.unit_factor(t["units"], fz, "force") if fz else 1.0
        loads = defaultdict(lambda: [0.0, 0.0])
        for r in t["records"]:
            p = str(MR.pick(r, "Label", "Point", "Joint", "UniqueName"))
            case = str(MR.pick(r, "Output Case", "OutputCase", "Load Case/Combo", "Case") or "")
            v = MR.fnum(MR.pick(r, "FZ", "F3"))
            if v is None or str(MR.pick(r, "Step Type") or "").lower() == "min":
                continue
            if case in Dset:
                loads[p][0] += v * ff
            elif case in Lset:
                loads[p][1] += v * ff
        cols = MR.base_columns(M)
        for p, (D, L) in loads.items():
            c = cols.get(p)
            if not c or not c["D"]:
                res["skipped"].append(f"Reaction at point {p} (D={D:.0f}, L={L:.0f} kN): no column - wall or strip "
                                      f"footing, design manually.")
                continue
            ca, cb = round((c["B"] or c["D"]) * 1000), round(c["D"] * 1000)
            if abs((c.get("ang") or 0) % 180 - 90) < 1:
                ca, cb = cb, ca
            rep = design_isolated_footing(ca, cb, round(D, 1), round(L, 1), a.q_allow, fcu=a.fcu_found, fy=a.fy,
                                          title=f"Footing at point {p}")
            reports.append(("footings", rep))
            r = rep.results
            dims = [int(x) for x in re.findall(r"\d+", r.get("B × L × h", ""))[:3]]
            res["footings"].append({"point": p, "x": c["x"], "y": c["y"], "col": (ca, cb), "D": D, "L": L,
                                    "B": dims[0], "Lf": dims[1], "h": dims[2],
                                    "bars_L": r.get("bars_along_L", ""), "bars_B": r.get("bars_along_B", ""),
                                    "ok": rep.ok, "fail": [c_.desc for c_ in rep.checks if not c_.ok]})

    # ---- members from forces
    if a.forces:
        for kind in ("column", "beam"):
            class A:  # minimal args object for MR._forces
                model, forces, combos = a.model, a.forces, a.combos
            try:
                _, env, sec = MR._forces(A, kind)
            except SystemExit as e:
                res["skipped"].append(str(e))
                continue
            for (st, lab), e in env.items():
                i = sec.get((st, lab))
                if not i or not i["D"]:
                    res["skipped"].append(f"{kind} {lab} @ {st}: no section in model")
                    continue
                b, h = round((i["B"] or i["D"]) * 1000), round(i["D"] * 1000)
                if kind == "column":
                    He = round(M.height(st) * 1000)
                    rep = design_column(b, h, a.fcu, a.fy, round(e["P"], 1), round(e["M3"], 1), round(e["M2"], 1),
                                        He, He, braced=not a.unbraced, title=f"Column {lab} - {st}")
                    r = rep.results
                    res["columns"].append({"label": lab, "story": st, "b": b, "t": h, "Pu": e["P"],
                                           "long": r.get("longitudinal", ""), "ties": r.get("ties", ""),
                                           "ok": rep.ok, "fail": [c_.desc for c_ in rep.checks if not c_.ok],
                                           "elev": M.elev(st)})
                else:
                    rep = design_beam(b, h, a.fcu, a.fy, round(e["M3pos"], 1), round(e["M3neg"], 1), round(e["V2"], 1),
                                      title=f"Beam {lab} - {st}")
                    r = rep.results
                    res["beams"].append({"label": lab, "story": st, "b": b, "h": h,
                                         "bot": r.get("positive.tension_bars", ""), "top": r.get("negative.tension_bars", ""),
                                         "stir": r.get("shear.stirrups", ""), "ok": rep.ok,
                                         "fail": [c_.desc for c_ in rep.checks if not c_.ok], "elev": M.elev(st)})
                reports.append((kind + "s", rep))
    # ---- slabs and walls
    from ecp203.slab import design_two_way_slab, design_one_way_slab
    from ecp203.floor_flat import design_flat_slab_floor
    from ecp203.wall import design_wall
    if not a.no_slabs:
        res["slabs"] = SW.design_slabs(M, a, (design_two_way_slab, design_one_way_slab, design_flat_slab_floor),
                                       reports, res["skipped"])
    else:
        res["slabs"] = {"panels": [], "flat": []}
    res["walls"] = SW.design_walls(M, a, design_wall, reports, res["skipped"]) if not a.no_walls else []
    return res, reports


def group(items, keyf, prefix, sizef):
    types = OrderedDict()
    for it in items:
        types.setdefault(keyf(it), []).append(it)
    ordered = sorted(types.items(), key=lambda kv: -sizef(kv[1][0]))
    out = []
    for n, (k, lst) in enumerate(ordered, 1):
        name = f"{prefix}{n}"
        for it in lst:
            it["type"] = name
        out.append((name, lst))
    return out


# ---------------------------------------------------------------- drawing helpers
class Sheet:
    def __init__(self, template, scale):
        import ezdxf
        self.ezdxf = ezdxf
        self.doc = ezdxf.readfile(template) if template else ezdxf.new("R2018", setup=True)
        self.msp = self.doc.modelspace()
        self.N = scale
        for name, col in (("GN-GRID", 8), ("GN-GRID-TAG", 7), ("GN-DIM", 7), ("GN-TEXT", 7), ("ST-COL", 4),
                          ("ST-BEAM", 3), ("ST-FNDN", 2), ("ST-RFT", 1), ("ST-TEXT", 7), ("GN-NPLT", 9)):
            if name not in self.doc.layers:
                self.doc.layers.add(name, color=col)
        self.style = "AH-EN" if "AH-EN" in self.doc.styles else "Standard"

    def th(self, paper_mm=2.5):
        return paper_mm * self.N

    def text(self, s, x, y, h=2.5, layer="ST-TEXT", align="LEFT"):
        from ezdxf.enums import TextEntityAlignment
        t = self.msp.add_text(str(s), height=self.th(h), dxfattribs={"layer": layer, "style": self.style})
        al = {"LEFT": TextEntityAlignment.BOTTOM_LEFT, "CENTER": TextEntityAlignment.MIDDLE_CENTER,
              "RIGHT": TextEntityAlignment.BOTTOM_RIGHT}[align]
        t.set_placement((x, y), align=al)
        return t

    def rect(self, x, y, w, h, layer, closed=True, solid=False):
        att = {"layer": layer}
        if solid:
            att["linetype"] = "Continuous"
        self.msp.add_lwpolyline([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], close=closed, dxfattribs=att)

    def line(self, p1, p2, layer):
        self.msp.add_line(p1, p2, dxfattribs={"layer": layer})

    def circle(self, c, r, layer, fill=False):
        self.msp.add_circle(c, r, dxfattribs={"layer": layer})
        if fill:
            h = self.msp.add_hatch(color=256, dxfattribs={"layer": layer})
            h.paths.add_edge_path().add_arc(c, r, 0, 360)

    def dim(self, p1, p2, offset, layer="GN-DIM"):
        dimstyle = f"AH-1-{self.N}" if f"AH-1-{self.N}" in self.doc.dimstyles else "Standard"
        x1, y1 = p1
        x2, y2 = p2
        if abs(y2 - y1) < 1e-6:
            base = (x1, y1 + offset)
            angle = 0
        else:
            base = (x1 + offset, y1)
            angle = 90
        d = self.msp.add_linear_dim(base=base, p1=p1, p2=p2, angle=angle, dimstyle=dimstyle,
                                    override={"dimtxt": self.th(2.0), "dimasz": self.th(1.5), "dimexo": self.th(0.8),
                                              "dimexe": self.th(0.8), "dimdec": 0, "dimtad": 1, "dimgap": self.th(0.5)},
                                    dxfattribs={"layer": layer})
        d.render()

    def table(self, x, y, headers, rows, widths, h=2.5):
        rh = self.th(h) * 2.4
        tw = sum(widths)
        allrows = [headers] + rows
        for i, row in enumerate(allrows):
            yy = y - (i + 1) * rh
            self.rect(x, yy, tw, rh, "GN-TEXT")
            cx = x
            for j, cell in enumerate(row):
                self.text(cell, cx + self.th(1), yy + rh * 0.3, h, "ST-TEXT")
                cx += widths[j]
                if j < len(row) - 1:
                    self.line((cx, yy), (cx, yy + rh), "GN-TEXT")
        return y - len(allrows) * rh

    def finish(self, path, title_fields, extents=None):
        """Paper space A1 viewport at scale 1:N and title block attributes."""
        from ezdxf import bbox
        box = bbox.extents(self.msp)
        if "A1" in self.doc.layouts.names():
            lay = self.doc.layouts.get("A1")
            ins = next((e for e in lay if e.dxftype() == "INSERT" and e.dxf.name == "AH-TITLE"), None)
            if ins is not None:
                for att in ins.attribs:
                    if att.dxf.tag in title_fields:
                        att.dxf.text = title_fields[att.dxf.tag]
                tb_left = ins.dxf.insert.x
            else:
                tb_left = 841 - 190
            if box.has_data:
                vw, vh = tb_left - 20, 574
                cx, cy = (box.extmin.x + box.extmax.x) / 2, (box.extmin.y + box.extmax.y) / 2
                lay.add_viewport(center=(10 + vw / 2, 10 + vh / 2), size=(vw, vh), view_center_point=(cx, cy),
                                 view_height=vh * self.N)
        self.doc.header["$INSUNITS"] = 4
        self.doc.saveas(path)
        return box

    def fits(self):
        from ezdxf import bbox
        box = bbox.extents(self.msp)
        w = (box.extmax.x - box.extmin.x) / self.N
        h = (box.extmax.y - box.extmin.y) / self.N
        return w <= 841 - 200 - 20 and h <= 574


def nice_scales():
    return [50, 75, 100, 125, 150, 200, 250, 300, 400, 500]


def grid_lines(M, xs, ys):
    """Return [(coord, label)] for X (numbers) and Y (letters) using model grid labels where they match."""
    gx, gy = {}, {}
    # model grids (if any) are listed under GRID lines; MR ignores them, so re-read quickly
    return ([(x, str(i + 1)) for i, x in enumerate(xs)],
            [(y, chr(ord("A") + i) if i < 26 else f"A{i - 25}") for i, y in enumerate(ys)])


def uniq(vals, tol=0.01):
    out = []
    for v in sorted(vals):
        if not out or abs(v - out[-1]) > tol:
            out.append(v)
    return out


# ---------------------------------------------------------------- sheet 1: foundations
def draw_foundations(res, ftypes, template, a, path):
    fts = res["footings"]
    xs = uniq([f["x"] for f in fts])
    ys = uniq([f["y"] for f in fts])
    x0, y0 = xs[0], ys[0]

    def P(x, y):
        return ((x - x0) * 1000, (y - y0) * 1000)

    for N in nice_scales():
        S = Sheet(template, N)
        gx, gy = grid_lines(res["model"], xs, ys)
        ext = 1500
        W = (xs[-1] - x0) * 1000
        H = (ys[-1] - y0) * 1000
        for x, lab in gx:
            X = (x - x0) * 1000
            S.line((X, -ext), (X, H + ext), "GN-GRID")
            S.circle((X, -ext - S.th(4)), S.th(4), "GN-GRID-TAG")
            S.text(lab, X, -ext - S.th(4), 4, "GN-GRID-TAG", "CENTER")
        for y, lab in gy:
            Y = (y - y0) * 1000
            S.line((-ext, Y), (W + ext, Y), "GN-GRID")
            S.circle((-ext - S.th(4), Y), S.th(4), "GN-GRID-TAG")
            S.text(lab, -ext - S.th(4), Y, 4, "GN-GRID-TAG", "CENTER")
        for i in range(len(gx) - 1):
            S.dim(((gx[i][0] - x0) * 1000, H), ((gx[i + 1][0] - x0) * 1000, H), ext * 0.6)
        for i in range(len(gy) - 1):
            S.dim((W, (gy[i][0] - y0) * 1000), (W, (gy[i + 1][0] - y0) * 1000), ext * 0.6)
        for f in fts:
            cx, cy = P(f["x"], f["y"])
            ca, cb = f["col"]
            # footing L along column D (= along X for ANG 0), B along Y
            S.rect(cx - f["Lf"] / 2, cy - f["B"] / 2, f["Lf"], f["B"], "ST-FNDN")
            S.rect(cx - cb / 2, cy - ca / 2, cb, ca, "ST-COL")
            S.text(f["type"], cx + cb / 2 + S.th(1), cy + ca / 2 + S.th(0.5), 3.0, "ST-TEXT")
        S.text("FOUNDATION PLAN", W / 2, -ext - S.th(16), 5, "ST-TEXT", "CENTER")
        S.text(f"Scale 1:{N}", W / 2, -ext - S.th(22), 3, "ST-TEXT", "CENTER")
        # schedule
        tx = W + ext + S.th(20)
        rows = []
        for name, lst in ftypes:
            f = lst[0]
            rows.append([name, f"{f['B']} x {f['Lf']} x {f['h']}", short(f["bars_L"]), short(f["bars_B"]),
                         f"{f['col'][0]}x{f['col'][1]}", str(len(lst)),
                         ", ".join(sorted(x["point"] for x in lst))[:40], "OK" if all(x["ok"] for x in lst) else "CHECK"])
        S.text("FOOTING SCHEDULE", tx, H + ext, 4, "ST-TEXT")
        yb = S.table(tx, H + ext - S.th(3), ["Type", "B x L x h (mm)", "Bars // L", "Bars // B", "Column", "No.",
                                              "Points", "ECP 203"], rows,
                     [S.th(12), S.th(42), S.th(24), S.th(24), S.th(20), S.th(10), S.th(40), S.th(18)])
        notes = [f"Concrete fcu = {a.fcu_found} N/mm2 (cube), steel fy = {a.fy} N/mm2, cover 75 mm, PC blinding 100 mm.",
                 f"Net allowable soil pressure = {a.q_allow} kN/m2 (from soil report - verify).",
                 "Bars // L run along the footing length L (plan X direction); bottom mesh.",
                 "Footing bars hooked 90 deg at ends where straight length is not sufficient (see calc. report).",
                 "Dimensions in mm, levels in m. Generated from analysis - engineer to review before issue."]
        for k, n in enumerate(notes):
            S.text(f"{k + 1}. {n}", tx, yb - S.th(6) - k * S.th(5), 2.5, "ST-TEXT")
        # details per type: plan + section
        dy = -ext - S.th(40)
        dx = 0
        for name, lst in ftypes:
            f = lst[0]
            Bf, Lf, h = f["B"], f["Lf"], f["h"]
            ca, cb = f["col"]
            ox, oy = dx, dy - Bf
            S.text(f"{name} - PLAN", ox + Lf / 2, oy + Bf + S.th(13), 3, "ST-TEXT", "CENTER")
            S.rect(ox, oy, Lf, Bf, "ST-FNDN")
            S.rect(ox + Lf / 2 - cb / 2, oy + Bf / 2 - ca / 2, cb, ca, "ST-COL")
            nL, dL = bars_per_m(f["bars_L"])
            nB, dB = bars_per_m(f["bars_B"])
            c = 75
            if nL:
                sp = 1000 / nL
                k = 0
                yy = oy + c
                while yy <= oy + Bf - c + 1 and k < 60:
                    if k % 2 == 0:
                        S.line((ox + c, yy), (ox + Lf - c, yy), "ST-RFT")
                    yy += sp
                    k += 1
            if nB:
                sp = 1000 / nB
                k = 0
                xx = ox + c
                while xx <= ox + Lf - c + 1 and k < 60:
                    if k % 2 == 0:
                        S.line((xx, oy + c), (xx, oy + Bf - c), "ST-RFT")
                    xx += sp
                    k += 1
            S.text(short(f["bars_L"]) + " bot.", ox + Lf + S.th(2), oy + Bf * 0.3, 2.5, "ST-TEXT")
            S.text(short(f["bars_B"]) + " bot.", ox + Lf * 0.3, oy - S.th(5), 2.5, "ST-TEXT")
            S.dim((ox, oy + Bf), (ox + Lf, oy + Bf), S.th(4))
            S.dim((ox, oy), (ox, oy + Bf), -S.th(6))
            # section along L
            sy = oy - S.th(28) - h - 600
            S.text(f"{name} - SECTION", ox + Lf / 2, sy + h + 600 + S.th(5), 3, "ST-TEXT", "CENTER")
            S.rect(ox - 100, sy - 100, Lf + 200, 100, "ST-FNDN")  # blinding
            S.rect(ox, sy, Lf, h, "ST-FNDN")
            S.line((ox + Lf / 2 - cb / 2, sy + h), (ox + Lf / 2 - cb / 2, sy + h + 600), "ST-COL")
            S.line((ox + Lf / 2 + cb / 2, sy + h), (ox + Lf / 2 + cb / 2, sy + h + 600), "ST-COL")
            hk = min(h - 2 * c, 12 * (dL or 12))
            S.msp.add_lwpolyline([(ox + c, sy + c + hk), (ox + c, sy + c), (ox + Lf - c, sy + c),
                                  (ox + Lf - c, sy + c + hk)], dxfattribs={"layer": "ST-RFT"})
            if nB:
                sp = 1000 / nB
                xx = ox + c + sp / 2
                while xx < ox + Lf - c:
                    S.circle((xx, sy + c + (dL or 12) + (dB or 12) / 2), (dB or 12) / 2 + 4, "ST-RFT")
                    xx += sp
            S.text(short(f["bars_L"]), ox + Lf / 2, sy - S.th(8), 2.5, "ST-TEXT", "CENTER")
            S.dim((ox, sy), (ox + Lf, sy), -S.th(14))
            S.dim((ox + Lf, sy), (ox + Lf, sy + h), S.th(5))
            S.text("PC 100", ox - 100 - S.th(14), sy - 100, 2.0, "ST-TEXT")
            dx += max(Lf, Bf) + S.th(55)
        if S.fits():
            break
    box = S.finish(path, a.title_fields(f"FOUNDATION PLAN & FOOTING DETAILS", "101", N, "ZZ"))
    return N


# ---------------------------------------------------------------- sheet 2: columns
def bar_positions(b, t, n, cover, dt, db):
    """Symmetric layout: 4 corners + remaining split on faces proportionally to their length."""
    xi, yi = cover + dt + db / 2, cover + dt + db / 2
    xa, ya = b - xi, t - yi
    pts = [(xi, yi), (xa, yi), (xa, ya), (xi, ya)]
    rest = max(n - 4, 0)
    pairs = rest // 2
    on_b = round(pairs * b / (b + t))  # extra bars per face along b (each of 2 faces)
    on_t = pairs - on_b
    for k in range(1, on_b + 1):
        x = xi + (xa - xi) * k / (on_b + 1)
        pts += [(x, yi), (x, ya)]
    for k in range(1, on_t + 1):
        y = yi + (ya - yi) * k / (on_t + 1)
        pts += [(xi, y), (xa, y)]
    return pts


def draw_columns(res, ctypes, template, a, path):
    for N in (10, 15, 20, 25, 30, 40, 50):
        S = Sheet(template, N)
        x = 0
        maxh = max(t for _, lst in ctypes for t in [lst[0]["t"]])
        for name, lst in ctypes:
            c = lst[0]
            b, t = c["b"], c["t"]
            n, d = bars_n(c["long"])
            dt, s = ties(c["ties"])
            S.text(name, x + b / 2, maxh + S.th(12), 4, "ST-TEXT", "CENTER")
            S.rect(x, 0, b, t, "ST-COL")
            cv = 25
            S.rect(x + cv, cv, b - 2 * cv, t - 2 * cv, "ST-RFT")
            for (px, py) in bar_positions(b, t, n, cv, dt, d):
                S.circle((x + px, py), d / 2, "ST-RFT", fill=True)
            S.dim((x, t), (x + b, t), S.th(4))
            S.dim((x + b, 0), (x + b, t), S.th(4))
            S.text(f"{n}T{d}", x + b / 2, -S.th(6), 2.5, "ST-TEXT", "CENTER")
            S.text(f"Ties T{dt}@{s}", x + b / 2, -S.th(11), 2.5, "ST-TEXT", "CENTER")
            x += max(b, 300) + S.th(40)
        rows = []
        by_label = defaultdict(dict)
        stories = sorted({c["story"] for c in res["columns"]}, key=lambda s: -(next(
            (cc["elev"] for cc in res["columns"] if cc["story"] == s), 0) or 0))
        for c in res["columns"]:
            by_label[c["label"]][c["story"]] = c["type"] + ("" if c["ok"] else "*")
        S.text("COLUMN TYPES", 0, maxh + S.th(24), 5, "ST-TEXT")
        ty = -S.th(25)
        tw = [S.th(16)] + [S.th(16)] * len(stories)
        yb = S.table(0, ty, ["Column"] + stories,
                     [[lab] + [v.get(st, "-") for st in stories] for lab, v in sorted(by_label.items())], tw)
        trows = [[name, f"{lst[0]['b']}x{lst[0]['t']}", short(lst[0]["long"]), short(lst[0]["ties"]), str(len(lst))]
                 for name, lst in ctypes]
        tx = sum(tw) + S.th(20)
        S.table(tx, ty, ["Type", "b x t (mm)", "Main bars", "Ties", "No."], trows,
                [S.th(12), S.th(24), S.th(24), S.th(22), S.th(10)])
        notes = [f"fcu = {a.fcu} N/mm2 (cube), fy = {a.fy} N/mm2, clear cover 25 mm.",
                 "* = element has a failing ECP 203 check: resize before issue (see reports).",
                 "Lap splices, tie spacing at joints and splice zones per ECP 203 detailing chapter.",
                 "t is along the column depth D in the model (local 2 axis)."]
        for k, nt in enumerate(notes):
            S.text(f"{k + 1}. {nt}", 0, yb - S.th(6) - k * S.th(5), 2.5, "ST-TEXT")
        if S.fits():
            break
    S.finish(path, a.title_fields("COLUMN SCHEDULE", "501", N, "ZZ"))
    return N


# ---------------------------------------------------------------- sheet 3: beams
def draw_beams(res, btypes, template, a, path):
    for N in (10, 15, 20, 25, 30, 40, 50):
        S = Sheet(template, N)
        x = 0
        maxh = max(lst[0]["h"] for _, lst in btypes)
        for name, lst in btypes:
            bm = lst[0]
            b, h = bm["b"], bm["h"]
            nb, db = bars_n(bm["bot"])
            nt, dtp = bars_n(bm["top"])
            m = re.search(r"Ø\s*(\d+)", bm["stir"] or "")
            ds = int(m.group(1)) if m else 8
            cv = 25
            S.text(name, x + b / 2, maxh + S.th(12), 4, "ST-TEXT", "CENTER")
            S.rect(x, 0, b, h, "ST-BEAM", solid=True)
            S.rect(x + cv, cv, b - 2 * cv, h - 2 * cv, "ST-RFT")
            for nn, dd, yy in ((nb, db, cv + ds + db / 2), (max(nt, 2), dtp or 12, h - cv - ds - (dtp or 12) / 2)):
                if nn <= 0:
                    continue
                xs_ = [cv + ds + dd / 2 + k * (b - 2 * (cv + ds) - dd) / max(nn - 1, 1) for k in range(nn)]
                for xx in xs_:
                    S.circle((x + xx, yy), dd / 2, "ST-RFT", fill=True)
            S.dim((x, h), (x + b, h), S.th(4))
            S.dim((x + b, 0), (x + b, h), S.th(4))
            S.text(f"Top {short(bm['top'])}", x + b / 2, -S.th(6), 2.5, "ST-TEXT", "CENTER")
            S.text(f"Bot {short(bm['bot'])}", x + b / 2, -S.th(11), 2.5, "ST-TEXT", "CENTER")
            S.text(f"Stir {short(bm['stir'])}", x + b / 2, -S.th(16), 2.5, "ST-TEXT", "CENTER")
            x += max(b, 300) + S.th(45)
        S.text("BEAM TYPES", 0, maxh + S.th(24), 5, "ST-TEXT")
        rows = []
        for name, lst in btypes:
            bm = lst[0]
            labs = ", ".join(sorted({f"{i['label']}@{i['story']}" for i in lst}))
            rows.append([name, f"{bm['b']}x{bm['h']}", short(bm["top"]), short(bm["bot"]), short(bm["stir"]),
                         labs if len(labs) <= 60 else labs[:57] + "...", "OK" if all(i["ok"] for i in lst) else "CHECK"])
        yb = S.table(0, -S.th(30), ["Type", "b x h (mm)", "Top (support)", "Bottom (span)", "Stirrups", "Beams",
                                    "ECP 203"], rows,
                     [S.th(12), S.th(24), S.th(28), S.th(28), S.th(26), S.th(95), S.th(18)])
        notes = [f"fcu = {a.fcu} N/mm2 (cube), fy = {a.fy} N/mm2, stirrups fy = 240 N/mm2, cover 25 mm.",
                 "Top bars over supports, bottom bars in span; curtailment and laps per ECP 203.",
                 "Rectangular sections designed (T-beam flange ignored - conservative)."]
        for k, nt in enumerate(notes):
            S.text(f"{k + 1}. {nt}", 0, yb - S.th(6) - k * S.th(5), 2.5, "ST-TEXT")
        if S.fits():
            break
    S.finish(path, a.title_fields("BEAM SCHEDULE", "502", N, "ZZ"))
    return N


def preview(dxf_path, png_path):
    try:
        import ezdxf
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from ezdxf.addons.drawing import Frontend, RenderContext
        from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
        doc = ezdxf.readfile(dxf_path)
        fig = plt.figure(figsize=(16, 11))
        ax = fig.add_axes([0, 0, 1, 1])
        Frontend(RenderContext(doc), MatplotlibBackend(ax)).draw_layout(doc.modelspace(), finalize=True)
        fig.savefig(png_path, dpi=110, facecolor="white")
        plt.close(fig)
        return True
    except Exception as e:  # preview is optional
        print(f"  (preview skipped: {e})")
        return False


def write_xlsx(res, path):
    import openpyxl
    from openpyxl.styles import Font
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Footings"
    ws.append(["Type", "Point", "X m", "Y m", "Column", "D kN", "L kN", "B mm", "L mm", "h mm", "Bars // L", "Bars // B",
               "OK", "Failing checks"])
    for f in sorted(res["footings"], key=lambda f: f["type"]):
        ws.append([f["type"], f["point"], round(f["x"], 3), round(f["y"], 3), f"{f['col'][0]}x{f['col'][1]}",
                   round(f["D"], 1), round(f["L"], 1), f["B"], f["Lf"], f["h"], short(f["bars_L"]), short(f["bars_B"]),
                   "yes" if f["ok"] else "NO", "; ".join(f["fail"])])
    ws = wb.create_sheet("Columns")
    ws.append(["Type", "Column", "Story", "b mm", "t mm", "Pu kN", "Main bars", "Ties", "OK", "Failing checks"])
    for c in sorted(res["columns"], key=lambda c: (c["type"], c["label"])):
        ws.append([c["type"], c["label"], c["story"], c["b"], c["t"], round(c["Pu"], 1), short(c["long"]),
                   short(c["ties"]), "yes" if c["ok"] else "NO", "; ".join(c["fail"])])
    ws = wb.create_sheet("Beams")
    ws.append(["Type", "Beam", "Story", "b mm", "h mm", "Top", "Bottom", "Stirrups", "OK", "Failing checks"])
    for b in sorted(res["beams"], key=lambda b: (b["type"], b["label"])):
        ws.append([b["type"], b["label"], b["story"], b["b"], b["h"], short(b["top"]), short(b["bot"]), short(b["stir"]),
                   "yes" if b["ok"] else "NO", "; ".join(b["fail"])])
    ws = wb.create_sheet("Slabs")
    ws.append(["Type", "Story", "X from", "X to", "Y from", "Y to", "t mm", "Mode", "wD kN/m2", "wL kN/m2",
               "Continuous sides", "Bottom X", "Bottom Y", "Top X", "Top Y", "OK", "Failing checks"])
    for q in sorted(res["slabs"]["panels"], key=lambda q: (q["type"], q["story"])):
        ws.append([q["type"], q["story"], q["x0"], q["x1"], q["y0"], q["y1"], q["t"], q["mode"], q["wD"], round(q["wL"], 2),
                   "".join(k for k, v in q["cont"].items() if v) or "-", short(q["bx"]), short(q["by"]),
                   short(q["tx"]), short(q["ty"]), "yes" if q["ok"] else "NO", "; ".join(q["fail"])])
    if res["slabs"]["flat"]:
        ws = wb.create_sheet("Flat slab strips")
        ws.append(["Story", "h mm", "Frame", "Span", "Section", "Layer", "M kN.m", "Column strip", "Middle strip"])
        for fl in res["slabs"]["flat"]:
            for s_ in fl["results"].get("strips", []):
                ws.append([fl["story"], fl["h"], s_["frame"], s_["span"] + 1, s_["section"], s_["layer"], s_["M_kNm"],
                           short(s_["column_strip"] or ""), short(s_["middle_strip"] or "")])
        ws = wb.create_sheet("Punching")
        ws.append(["Story", "Grid i (X)", "Grid j (Y)", "Location", "Pu kN", "Ratio", "OK"])
        for fl in res["slabs"]["flat"]:
            for pz in fl["results"].get("punching", []):
                ws.append([fl["story"], pz["i"] + 1, chr(65 + pz["j"]), pz["location"], pz["Pu_kN"], pz["ratio"],
                           "yes" if pz["ratio"] <= 1 else "NO"])
    ws = wb.create_sheet("Walls")
    ws.append(["Type", "Pier", "Story", "t mm", "L m", "H clear m", "Pu kN/m", "Vertical / face", "Horizontal / face",
               "OK", "Failing checks"])
    for w in sorted(res["walls"], key=lambda w: (w["type"], w["pier"])):
        ws.append([w["type"], w["pier"], w["story"], w["t"], round(w["L"], 2), w["H"], round(w["Pu_m"], 1),
                   short(w["vert"]), short(w["hor"]), "yes" if w["ok"] else "NO", "; ".join(w["fail"])])
    for w in wb.worksheets:
        for c in w[1]:
            c.font = Font(bold=True)
        for col in w.columns:
            w.column_dimensions[col[0].column_letter].width = max(10, min(45, max(len(str(c.value or "")) for c in col) + 2))
    wb.save(path)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--model", required=True)
    p.add_argument("--reactions")
    p.add_argument("--forces")
    p.add_argument("--combos", help="ultimate combinations for members (default: all in the table)")
    p.add_argument("--q-allow", type=float, default=None, help="net allowable soil pressure kN/m2 (needed for footings)")
    p.add_argument("--fcu", type=float, default=30, help="cube strength for columns/beams N/mm2")
    p.add_argument("--fcu-found", type=float, default=25, help="cube strength for footings N/mm2")
    p.add_argument("--fy", type=float, default=400)
    p.add_argument("--fy-slab", type=float, default=None, help="steel for slabs (default = --fy)")
    p.add_argument("--no-slabs", action="store_true")
    p.add_argument("--no-walls", action="store_true")
    p.add_argument("--dead-cases")
    p.add_argument("--live-cases")
    p.add_argument("--unbraced", action="store_true")
    p.add_argument("--project", default="PROJECT")
    p.add_argument("--client", default="-")
    p.add_argument("--project-code", default="PRJ", help="2-5 capital letters for drawing numbers")
    p.add_argument("--lib", help="path to the 'Egyptian codes' folder")
    p.add_argument("--template", help="AH-template.dxf (auto-detected from alhabeeb-cad-standards)")
    p.add_argument("-o", "--out", required=True)
    a = p.parse_args()
    if a.reactions and a.q_allow is None:
        sys.exit("--q-allow is required to design footings (from the soil report)")
    lib = a.lib or find_lib(os.path.dirname(os.path.abspath(a.model)))
    if not lib:
        sys.exit("Cannot find 'Egyptian codes/ecp203'; pass --lib")
    tpl = a.template or find_template()
    os.makedirs(os.path.join(a.out, "reports"), exist_ok=True)

    a.fy_slab = a.fy_slab or a.fy

    def title_fields(title, num, N, loc, level="ZZ"):
        return {"PROJECT": a.project, "CLIENT": a.client, "DWG_TITLE": title, "LEVEL": level, "DWG_NO": f"{a.project_code}-ST-{loc}-{num}",
                "REV": "R00", "SCALE": f"1:{N}", "SHEET_SIZE": "A1", "PURPOSE": "للمراجعة", "DRAWN": "Claude (auto)"}
    a.title_fields = title_fields

    res, reports = design_all(a, lib)
    ftypes = group(res["footings"], lambda f: (f["B"], f["Lf"], f["h"], short(f["bars_L"]), short(f["bars_B"]), f["col"]),
                   "F", lambda f: f["B"] * f["Lf"])
    ctypes = group(res["columns"], lambda c: (c["b"], c["t"], short(c["long"]), short(c["ties"])), "CT",
                   lambda c: c["b"] * c["t"] * 100 + bars_n(c["long"])[0] * bars_n(c["long"])[1] ** 2)
    btypes = group(res["beams"], lambda b: (b["b"], b["h"], short(b["top"]), short(b["bot"]), short(b["stir"])), "BT",
                   lambda b: b["b"] * b["h"] * 100 + bars_n(b["bot"])[0] * bars_n(b["bot"])[1] ** 2)

    ptypes = group(res["slabs"]["panels"], lambda q: (q["t"], q["mode"], short(q["bx"]), short(q["by"]),
                                                       short(q["tx"]), short(q["ty"])), "S",
                   lambda q: (q["x1"] - q["x0"]) * (q["y1"] - q["y0"]))
    wtypes = group(res["walls"], lambda w: (w["t"], short(w["vert"]), short(w["hor"])), "WT",
                   lambda w: w["t"] * 1000 + bars_per_m(w["vert"])[0] * (bars_per_m(w["vert"])[1] or 0) ** 2
                   if bars_per_m(w["vert"])[0] else w["t"])
    for kind in ("footings", "columns", "beams", "slabs", "walls"):
        md = "\n\n".join(r.to_markdown() for k, r in reports if k == kind)
        if md:
            with open(os.path.join(a.out, "reports", f"{kind}.md"), "w", encoding="utf-8") as f:
                f.write(md)
    write_xlsx(res, os.path.join(a.out, "design.xlsx"))
    sheets = []
    if ftypes:
        fp = os.path.join(a.out, f"{a.project_code}-ST-ZZ-101_R00.dxf")
        N = draw_foundations(res, ftypes, tpl, a, fp)
        sheets.append((fp, N))
    if ctypes:
        fp = os.path.join(a.out, f"{a.project_code}-ST-ZZ-501_R00.dxf")
        sheets.append((fp, draw_columns(res, ctypes, tpl, a, fp)))
    if btypes:
        fp = os.path.join(a.out, f"{a.project_code}-ST-ZZ-502_R00.dxf")
        sheets.append((fp, draw_beams(res, btypes, tpl, a, fp)))
    stories = [s["name"] for s in res["model"].stories]
    k = 0
    for st in stories:
        pans = [q for q in res["slabs"]["panels"] if q["story"] == st]
        if pans:
            k += 1
            fp = os.path.join(a.out, f"{a.project_code}-ST-ZZ-{110 + k}_R00.dxf")
            S, N = SW.draw_slab_story(Sheet, tpl, res["model"], st, pans, ptypes, a, fp, short, bars_per_m)
            S.finish(fp, a.title_fields(f"SLAB REINFORCEMENT - {st}", str(110 + k), N, "ZZ", st))
            sheets.append((fp, N))
    for fl in res["slabs"]["flat"]:
        k += 1
        fp = os.path.join(a.out, f"{a.project_code}-ST-ZZ-{110 + k}_R00.dxf")
        S, N = SW.draw_flat_story(Sheet, tpl, res["model"], fl, a, fp, short)
        S.finish(fp, a.title_fields(f"FLAT SLAB REINFORCEMENT - {fl['story']}", str(110 + k), N, "ZZ", fl["story"]))
        sheets.append((fp, N))
    if wtypes:
        fp = os.path.join(a.out, f"{a.project_code}-ST-ZZ-503_R00.dxf")
        S, N = SW.draw_walls(Sheet, tpl, wtypes, a, short, bars_per_m)
        S.finish(fp, a.title_fields("WALL SCHEDULE", "503", N, "ZZ"))
        sheets.append((fp, N))
    for fp, N in sheets:
        preview(fp, fp[:-4] + ".png")

    nf = lambda lst: sum(1 for x in lst if not x["ok"])  # noqa: E731
    print(f"Footings: {len(res['footings'])} in {len(ftypes)} types ({nf(res['footings'])} failing)")
    for name, lst in ftypes:
        f = lst[0]
        print(f"  {name}: {f['B']}x{f['Lf']}x{f['h']}  {short(f['bars_L'])} / {short(f['bars_B'])}  x{len(lst)}"
              + ("" if all(i["ok"] for i in lst) else "  FAILS: " + "; ".join(sorted({x for i in lst for x in i["fail"]}))))
    print(f"Columns: {len(res['columns'])} in {len(ctypes)} types ({nf(res['columns'])} failing)")
    for name, lst in ctypes:
        c = lst[0]
        print(f"  {name}: {c['b']}x{c['t']}  {short(c['long'])}  {short(c['ties'])}  x{len(lst)}"
              + ("" if all(i["ok"] for i in lst) else "  FAILS: " + "; ".join(sorted({x for i in lst for x in i["fail"]}))))
    print(f"Beams: {len(res['beams'])} in {len(btypes)} types ({nf(res['beams'])} failing)")
    for name, lst in btypes:
        b = lst[0]
        print(f"  {name}: {b['b']}x{b['h']}  top {short(b['top'])}  bot {short(b['bot'])}  {short(b['stir'])}  x{len(lst)}"
              + ("" if all(i["ok"] for i in lst) else "  FAILS: " + "; ".join(sorted({x for i in lst for x in i["fail"]}))))
    print(f"Slabs: {len(res['slabs']['panels'])} panels in {len(ptypes)} types "
          f"({nf(res['slabs']['panels'])} failing), {len(res['slabs']['flat'])} flat-slab floors")
    for name, lst in ptypes:
        q = lst[0]
        print(f"  {name}: t={q['t']} {q['mode']}  bot X {short(q['bx'])} Y {short(q['by'])}  top X {short(q['tx'])} "
              f"Y {short(q['ty'])}  x{len(lst)}"
              + ("" if all(i["ok"] for i in lst) else "  FAILS: " + "; ".join(sorted({x for i in lst for x in i["fail"]}))))
    for fl in res["slabs"]["flat"]:
        print(f"  flat {fl['story']}: h={fl['h']}  max punching {fl['results'].get('max_punching_ratio')}  "
              f"{len(fl['results'].get('strips', []))} strip sections" + ("" if fl["ok"] else "  FAILS: "
                                                                          + "; ".join(fl["fail"][:4])))
    print(f"Walls: {len(res['walls'])} piers in {len(wtypes)} types ({nf(res['walls'])} failing)")
    for name, lst in wtypes:
        w = lst[0]
        print(f"  {name}: t={w['t']}  vert {short(w['vert'])}  hor {short(w['hor'])} (each face)  x{len(lst)}"
              + ("" if all(i["ok"] for i in lst) else "  FAILS: " + "; ".join(sorted({x for i in lst for x in i["fail"]}))))
    for s in res["skipped"]:
        print("  skipped: " + s)
    print("Files:")
    for fp, N in sheets:
        print(f"  {fp}  (A1, 1:{N})")
    print(f"  {os.path.join(a.out, 'design.xlsx')}\n  {os.path.join(a.out, 'reports')}/*.md")


if __name__ == "__main__":
    main()
