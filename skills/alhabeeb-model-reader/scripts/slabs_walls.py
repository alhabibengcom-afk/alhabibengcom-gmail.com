"""Slab and wall design + drawings for building_design.py.

Slabs (per story, from the model geometry and its area loads - no SAFE export needed):
  * beam-supported panels: the slab is split on the grid of beam/wall/column lines; cells whose shared edge has no
    beam are merged. A rectangular region supported on all four sides is a panel -> ecp203 design_two_way_slab
    (which switches to one-way when r > 2), with continuity from neighbouring panels.
  * story with no beams -> flat slab: ecp203 design_flat_slab_floor on the column grid (equivalent frame +
    column/middle strips + punching at every column).
  * anything else (missing edge beam, cantilever, irregular region) is listed for manual design.
Walls: ETABS "Pier Forces" table (P per pier per story) + pier labels on wall areas -> ecp203 design_wall per
pier per story (Pu per metre = max compression / pier length; out-of-plane moment taken as 0 unless given).
"""
import math
import re
from collections import OrderedDict, defaultdict

import model_reader as MR

TOL = 0.02  # m


def _uniq(vals, tol=TOL):
    out = []
    for v in sorted(vals):
        if not out or abs(v - out[-1]) > tol:
            out.append(v)
    return out


def _inside(pt, poly):
    x, y = pt
    ins = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            xc = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if xc > x:
                ins = not ins
    return ins


def _covers(segs, p1, p2):
    """True if axis-aligned edge p1-p2 is covered by the union of collinear support segments."""
    (x1, y1), (x2, y2) = p1, p2
    horiz = abs(y1 - y2) < TOL
    lo, hi = (min(x1, x2), max(x1, x2)) if horiz else (min(y1, y2), max(y1, y2))
    ivs = []
    for (a, b) in segs:
        (ax, ay), (bx, by) = a, b
        if horiz and abs(ay - y1) < TOL and abs(by - y1) < TOL:
            ivs.append((min(ax, bx), max(ax, bx)))
        elif not horiz and abs(ax - x1) < TOL and abs(bx - x1) < TOL:
            ivs.append((min(ay, by), max(ay, by)))
    cur = lo
    for s, e in sorted(ivs):
        if s > cur + TOL:
            break
        cur = max(cur, e)
    return cur >= hi - TOL


def story_geometry(M, story):
    beams, walls, cols, slabs = [], [], [], []
    for a in M.line_assigns:
        if a["story"] != story:
            continue
        ln = M.lines.get(a["label"])
        if not ln:
            continue
        if ln["type"] == "BEAM" and ln["i"] in M.points and ln["j"] in M.points:
            shape, D, B = MR.sec_dims(M, a.get("SECTION"))
            beams.append({"label": a["label"], "p1": M.points[ln["i"]], "p2": M.points[ln["j"]], "b": B or 0.25,
                          "h": D or 0.5})
        elif ln["type"] == "COLUMN" and ln["i"] in M.points:
            shape, D, B = MR.sec_dims(M, a.get("SECTION"))
            cols.append({"label": a["label"], "xy": M.points[ln["i"]], "B": B or D or 0.3, "D": D or 0.3,
                         "section": a.get("SECTION")})
    for a in M.area_assigns:
        if a["story"] != story:
            continue
        ar = M.areas.get(a["label"])
        if not ar:
            continue
        sec = a.get("SECTION")
        kind = MR.shell_kind(M, sec, ar["type"])
        pts = [M.points[p] for p in ar["pts"] if p in M.points]
        if kind == "wall":
            u = []
            for p in pts:
                if all(math.hypot(p[0] - q[0], p[1] - q[1]) > TOL for q in u):
                    u.append(p)
            if len(u) >= 2:
                p1, p2 = max(((p, q) for p in u for q in u), key=lambda pq: math.hypot(pq[0][0] - pq[1][0],
                                                                                         pq[0][1] - pq[1][1]))
                walls.append({"label": a["label"], "p1": p1, "p2": p2, "t": MR.shell_t(M, sec) or 0.2,
                              "pier": a.get("PIER"), "section": sec})
        elif len(pts) >= 3:
            slabs.append({"label": a["label"], "poly": pts, "t": MR.shell_t(M, sec) or 0.15, "section": sec})
    return beams, walls, cols, slabs


def area_loads(M, story):
    """area label -> (SDL, LL) kN/m2 at this story (self-weight not included)."""
    types = {n: str(p.get("TYPE", "")).lower() for n, p in M.patterns.items()}
    f = M.ff / M.lf ** 2
    out = defaultdict(lambda: [0.0, 0.0])
    for ld in M.area_loads:
        if ld["story"] != story:
            continue
        lc = ld.get("LC") or ld.get("LOADPAT") or ld.get("PATTERN")
        v = MR.fnum(ld.get("FVAL"), 0.0) * f
        t = types.get(lc, "")
        if t in MR.DEAD_TYPES and t != "dead":
            out[ld["label"]][0] += v
        elif t == "dead":
            out[ld["label"]][0] += v
        elif t in MR.LIVE_TYPES:
            out[ld["label"]][1] += v
    return out


# ---------------------------------------------------------------- slab design
def design_slabs(M, a, lib_funcs, reports, skipped):
    design_two_way_slab, design_one_way_slab, design_flat_slab_floor = lib_funcs
    out = {"panels": [], "flat": []}
    for st in [s["name"] for s in M.stories[:-1]]:
        beams, walls, cols, slabs = story_geometry(M, st)
        if not slabs:
            continue
        loads = area_loads(M, st)
        sup = [(b["p1"], b["p2"]) for b in beams] + [(w["p1"], w["p2"]) for w in walls]
        if not beams:
            out["flat"] += _flat(M, st, cols, slabs, loads, a, design_flat_slab_floor, reports, skipped)
            continue
        xs = _uniq([p[0] for s in sup for p in s] + [c["xy"][0] for c in cols] + [p[0] for s in slabs for p in s["poly"]])
        ys = _uniq([p[1] for s in sup for p in s] + [c["xy"][1] for c in cols] + [p[1] for s in slabs for p in s["poly"]])
        cell = {}
        for i in range(len(xs) - 1):
            for j in range(len(ys) - 1):
                c = ((xs[i] + xs[i + 1]) / 2, (ys[j] + ys[j + 1]) / 2)
                s = next((s for s in slabs if _inside(c, s["poly"])), None)
                if s:
                    cell[(i, j)] = s
        # union cells across unsupported interior edges
        parent = {k: k for k in cell}

        def find(k):
            while parent[k] != k:
                parent[k] = parent[parent[k]]
                k = parent[k]
            return k

        for (i, j) in cell:
            if (i + 1, j) in cell and not _covers(sup, (xs[i + 1], ys[j]), (xs[i + 1], ys[j + 1])):
                parent[find((i, j))] = find((i + 1, j))
            if (i, j + 1) in cell and not _covers(sup, (xs[i], ys[j + 1]), (xs[i + 1], ys[j + 1])):
                parent[find((i, j))] = find((i, j + 1))
        regions = defaultdict(list)
        for k in cell:
            regions[find(k)].append(k)
        region_of = {k: r for r, ks in regions.items() for k in ks}
        for r, ks in regions.items():
            i0, i1 = min(k[0] for k in ks), max(k[0] for k in ks) + 1
            j0, j1 = min(k[1] for k in ks), max(k[1] for k in ks) + 1
            x0, x1, y0, y1 = xs[i0], xs[i1], ys[j0], ys[j1]
            rect = len(ks) == (i1 - i0) * (j1 - j0)
            edges = {"L": ((x0, y0), (x0, y1)), "R": ((x1, y0), (x1, y1)), "B": ((x0, y0), (x1, y0)),
                     "T": ((x0, y1), (x1, y1))}
            supported = {e: _covers(sup, *pp) for e, pp in edges.items()}
            s = cell[ks[0]]
            if not rect or not all(supported.values()):
                miss = [e for e, ok in supported.items() if not ok]
                skipped.append(f"Slab {st} region x {x0:.2f}-{x1:.2f}, y {y0:.2f}-{y1:.2f} m: "
                               + ("not rectangular" if not rect else f"no beam on side(s) {', '.join(miss)}")
                               + " (cantilever / flat part) - design manually.")
                continue
            # continuity: neighbour slab cell in a different region across each edge
            def nb(cells):
                return any(c in cell and region_of[c] != r for c in cells)
            cont = {"L": nb([(i0 - 1, j) for j in range(j0, j1)]), "R": nb([(i1, j) for j in range(j0, j1)]),
                    "B": nb([(i, j0 - 1) for i in range(i0, i1)]), "T": nb([(i, j1) for i in range(i0, i1)])}
            Lx, Ly = x1 - x0, y1 - y0
            t_mm = round(s["t"] * 1000)
            sdl, ll = loads.get(s["label"], (0.0, 0.0))
            wD = round(25 * s["t"] + sdl, 2)
            cx_, cy_ = cont["L"] + cont["R"], cont["B"] + cont["T"]
            rep = design_two_way_slab(round(Lx, 3), round(Ly, 3), wD, round(ll, 2), cx_, cy_, t=t_mm, fcu=a.fcu,
                                      fy=a.fy_slab, title=f"Slab {st} ({x0:g},{y0:g})-({x1:g},{y1:g})")
            reports.append(("slabs", rep))
            R = rep.results
            short_is_x = Lx <= Ly
            if "bottom_a" in R:
                bs, bl, ts, tl = R["bottom_a"], R.get("bottom_b", ""), R.get("top_a", ""), R.get("top_b", "")
                mode = "two-way"
            else:
                bs, bl, ts, tl = R.get("bottom", ""), R.get("distribution", ""), R.get("top", ""), ""
                mode = "one-way"
            bx, by = (bs, bl) if short_is_x else (bl, bs)
            tx, ty = (ts, tl) if short_is_x else (tl, ts)
            out["panels"].append({"label": s["label"], "cx": cx_, "cy": cy_, "story": st, "x0": x0, "x1": x1, "y0": y0, "y1": y1, "t": t_mm, "mode": mode,
                                  "wD": wD, "wL": ll, "cont": cont, "bx": bx, "by": by, "tx": tx, "ty": ty,
                                  "ok": rep.ok, "fail": [c.desc for c in rep.checks if not c.ok]})
    return out


def _flat(M, st, cols, slabs, loads, a, fn, reports, skipped, h_override=None):
    if len(cols) < 4:
        skipped.append(f"Slab {st}: no beams and fewer than 4 columns - design manually.")
        return []
    xs = _uniq([c["xy"][0] for c in cols])
    ys = _uniq([c["xy"][1] for c in cols])
    if len(cols) != len(xs) * len(ys):
        skipped.append(f"Slab {st}: flat slab with an irregular column grid ({len(cols)} columns on "
                       f"{len(xs)}x{len(ys)} lines) - the ecp203 equivalent-frame method needs a regular grid; "
                       f"design from SAFE strips.")
        return []
    s = slabs[0]
    h = h_override or round(s["t"] * 1000)
    sdl = max((loads.get(sl["label"], (0, 0))[0] for sl in slabs), default=0.0)
    ll = max((loads.get(sl["label"], (0, 0))[1] for sl in slabs), default=0.0)
    sizes = defaultdict(int)
    for c in cols:
        sizes[(round(c["D"] * 1000), round(c["B"] * 1000))] += 1
    col = max(sizes, key=sizes.get)
    override = {}
    for c in cols:
        sz = (round(c["D"] * 1000), round(c["B"] * 1000))
        if sz != col:
            override[(xs.index(min(xs, key=lambda v: abs(v - c["xy"][0]))),
                      ys.index(min(ys, key=lambda v: abs(v - c["xy"][1]))))] = sz
    Hb = M.height(st)
    names = [x["name"] for x in M.stories]
    above = names[names.index(st) - 1] if names.index(st) > 0 else None
    Ha = M.height(above) if above else Hb
    x0, y0 = xs[0], ys[0]
    rep = fn([round(v - x0, 3) for v in xs], [round(v - y0, 3) for v in ys], h, round(sdl, 2), round(ll, 2),
             fcu=a.fcu, fy=a.fy_slab, col=col, col_override=override or None, H_below=round(Hb, 2), H_above=round(Ha, 2),
             title=f"Flat slab {st}")
    reports.append(("slabs", rep))
    return [{"story": st, "xs": xs, "ys": ys, "h": h, "col": col, "sdl": sdl, "ll": ll, "results": rep.results,
             "ok": rep.ok, "fail": [c.desc for c in rep.checks if not c.ok]}]


# ---------------------------------------------------------------- wall design
def design_walls(M, a, design_wall, reports, skipped):
    out = []
    piers = defaultdict(list)  # (story, pier) -> walls
    for st in [s["name"] for s in M.stories[:-1]]:
        _, walls, _, slabs = story_geometry(M, st)
        for w in walls:
            piers[(st, w["pier"] or w["label"])].append(w)
    if not piers:
        return out
    forces = {}
    if a.forces:
        T = MR.read_any_tables(a.forces)
        _, t = MR.find_table(T, "pier")
        if t:
            combos = set(a.combos.split(",")) if a.combos else None
            pc = next((c for c in t["records"][0] if MR.norm(c) == "p"), None) if t["records"] else None
            pf = MR.unit_factor(t["units"], pc, "force") if pc else 1.0
            for r in t["records"]:
                case = str(MR.pick(r, "Output Case", "OutputCase", "Load Case/Combo", "Combo") or "")
                if combos and case not in combos:
                    continue
                key = (str(MR.pick(r, "Story") or ""), str(MR.pick(r, "Pier", "Label") or ""))
                P = -(MR.fnum(MR.pick(r, "P"), 0.0) or 0.0) * pf
                forces[key] = max(forces.get(key, 0.0), P)
    if not forces:
        skipped.append("Walls: no 'Pier Forces' table in the forces export (and pier labels on walls) - export it "
                       "from ETABS (Analysis Results > Wall Output > Pier Forces) to design walls.")
        return out
    for (st, pier), ws in piers.items():
        P = forces.get((st, pier))
        if P is None:
            skipped.append(f"Wall pier {pier} @ {st}: no forces in the Pier Forces table.")
            continue
        L = sum(math.hypot(w["p2"][0] - w["p1"][0], w["p2"][1] - w["p1"][1]) for w in ws)
        t = round(ws[0]["t"] * 1000)
        _, _, _, slabs = story_geometry(M, st)
        ts = max((s["t"] for s in slabs), default=0.0)
        H = round(M.height(st) - ts, 2)
        rep = design_wall(t, H, round(L, 2), a.fcu, a.fy, round(P / L, 1), 0.0, braced=not a.unbraced,
                          title=f"Wall {pier} - {st}")
        reports.append(("walls", rep))
        R = rep.results
        out.append({"story": st, "pier": pier, "t": t, "L": L, "H": H, "Pu_m": P / L, "vert": R.get("vertical", ""),
                    "hor": R.get("horizontal", ""), "walls": ws, "ok": rep.ok,
                    "fail": [c.desc for c in rep.checks if not c.ok]})
    return out


# ---------------------------------------------------------------- drawings
def _plan_base(S, M, st, beams, walls, cols, xs, ys, x0, y0, ext=1500):
    W, H = (xs[-1] - x0) * 1000, (ys[-1] - y0) * 1000
    for k, x in enumerate(xs):
        X = (x - x0) * 1000
        S.line((X, -ext), (X, H + ext), "GN-GRID")
        S.circle((X, -ext - S.th(4)), S.th(4), "GN-GRID-TAG")
        S.text(str(k + 1), X, -ext - S.th(4), 4, "GN-GRID-TAG", "CENTER")
    for k, y in enumerate(ys):
        Y = (y - y0) * 1000
        S.line((-ext, Y), (W + ext, Y), "GN-GRID")
        S.circle((-ext - S.th(4), Y), S.th(4), "GN-GRID-TAG")
        S.text(chr(65 + k) if k < 26 else f"A{k - 25}", -ext - S.th(4), Y, 4, "GN-GRID-TAG", "CENTER")
    for k in range(len(xs) - 1):
        S.dim(((xs[k] - x0) * 1000, H), ((xs[k + 1] - x0) * 1000, H), ext * 0.6)
    for k in range(len(ys) - 1):
        S.dim((W, (ys[k] - y0) * 1000), (W, (ys[k + 1] - y0) * 1000), ext * 0.6)

    def P(p):
        return ((p[0] - x0) * 1000, (p[1] - y0) * 1000)

    for b in beams:
        (ax, ay), (bx, by) = P(b["p1"]), P(b["p2"])
        L = math.hypot(bx - ax, by - ay) or 1
        nx, ny = -(by - ay) / L * b["b"] * 500, (bx - ax) / L * b["b"] * 500
        S.line((ax + nx, ay + ny), (bx + nx, by + ny), "ST-BEAM")
        S.line((ax - nx, ay - ny), (bx - nx, by - ny), "ST-BEAM")
    for w in walls:
        (ax, ay), (bx, by) = P(w["p1"]), P(w["p2"])
        L = math.hypot(bx - ax, by - ay) or 1
        nx, ny = -(by - ay) / L * w["t"] * 500, (bx - ax) / L * w["t"] * 500
        S.msp.add_lwpolyline([(ax + nx, ay + ny), (bx + nx, by + ny), (bx - nx, by - ny), (ax - nx, ay - ny)],
                             close=True, dxfattribs={"layer": "ST-WALL"})
    for c in cols:
        X, Y = P(c["xy"])
        d, b = c["D"] * 1000, c["B"] * 1000  # D along X (ANG 0)
        S.rect(X - d / 2, Y - b / 2, d, b, "ST-COL")
    return W, H, P


def draw_slab_story(Sheet, template, M, st, panels, ptypes, a, path, short, bars_per_m):
    beams, walls, cols, slabs = story_geometry(M, st)
    xs = _uniq([p["x0"] for p in panels] + [p["x1"] for p in panels] + [c["xy"][0] for c in cols])
    ys = _uniq([p["y0"] for p in panels] + [p["y1"] for p in panels] + [c["xy"][1] for c in cols])
    x0, y0 = xs[0], ys[0]
    for N in (50, 75, 100, 125, 150, 200, 250):
        S = Sheet(template, N)
        W, H, P = _plan_base(S, M, st, beams, walls, cols, xs, ys, x0, y0)
        for p in panels:
            X0, Y0 = P((p["x0"], p["y0"]))
            X1, Y1 = P((p["x1"], p["y1"]))
            cx, cy = (X0 + X1) / 2, (Y0 + Y1) / 2
            Lx, Ly = X1 - X0, Y1 - Y0
            S.text(f"{p['type']}  t={p['t']}", cx, cy + S.th(9), 3, "ST-TEXT", "CENTER")
            # bottom bars: one representative bar each way with hooks drawn as short ticks
            bx0, bx1 = X0 + 0.1 * Lx, X1 - 0.1 * Lx
            S.line((bx0, cy - S.th(3)), (bx1, cy - S.th(3)), "ST-RFT")
            S.line((bx0, cy - S.th(3)), (bx0, cy - S.th(5)), "ST-RFT")
            S.line((bx1, cy - S.th(3)), (bx1, cy - S.th(5)), "ST-RFT")
            S.text(f"B {short(p['bx'])}", cx + S.th(2), cy - S.th(2.5), 2.5, "ST-TEXT")
            by0, by1 = Y0 + 0.1 * Ly, Y1 - 0.1 * Ly
            S.line((cx - S.th(18), by0), (cx - S.th(18), by1), "ST-RFT")
            S.text(f"B {short(p['by'])}", cx - S.th(17), by0 + S.th(2), 2.5, "ST-TEXT")
            # top bars over each supported edge: L/4 of the shorter adjacent span each side (check ECP detailing)
            ext_x, ext_y = 0.25 * Lx, 0.25 * Ly
            for e, (xa, ya, xb, yb, lab) in {
                "L": (X0, cy + Ly * 0.25, X0 + ext_x, cy + Ly * 0.25, p["tx"]),
                "R": (X1 - ext_x, cy + Ly * 0.25, X1, cy + Ly * 0.25, p["tx"]),
                "B": (cx + Lx * 0.25, Y0, cx + Lx * 0.25, Y0 + ext_y, p["ty"]),
                "T": (cx + Lx * 0.25, Y1 - ext_y, cx + Lx * 0.25, Y1, p["ty"])}.items():
                if not lab or not p["cont"][e]:
                    continue
                S.line((xa, ya), (xb, yb), "ST-RFT")
                tick = S.th(1.5)
                if ya == yb:
                    S.line((xa, ya), (xa, ya - tick), "ST-RFT")
                    S.line((xb, yb), (xb, yb - tick), "ST-RFT")
                    S.text(f"T {short(lab)}", (xa + xb) / 2, ya + S.th(1), 2.0, "ST-TEXT", "CENTER")
                else:
                    S.line((xa, ya), (xa - tick, ya), "ST-RFT")
                    S.line((xb, yb), (xb - tick, yb), "ST-RFT")
                    S.text(f"T {short(lab)}", xa + S.th(1), (ya + yb) / 2, 2.0, "ST-TEXT")
        S.text(f"SLAB REINFORCEMENT - {st}", W / 2, -1500 - S.th(16), 5, "ST-TEXT", "CENTER")
        S.text(f"Scale 1:{N}", W / 2, -1500 - S.th(22), 3, "ST-TEXT", "CENTER")
        tx = W + 1500 + S.th(20)
        rows = [[n, str(l[0]["t"]), l[0]["mode"], short(l[0]["bx"]), short(l[0]["by"]), short(l[0]["tx"]) or "-",
                 short(l[0]["ty"]) or "-", str(sum(1 for i in l if i["story"] == st)), "OK" if all(i["ok"] for i in l) else "CHECK"]
                for n, l in ptypes if any(i["story"] == st for i in l)]
        S.text("SLAB SCHEDULE", tx, H + 1500, 4, "ST-TEXT")
        yb = S.table(tx, H + 1500 - S.th(3), ["Type", "t mm", "Mode", "Bottom X", "Bottom Y", "Top X", "Top Y", "No.",
                                              "ECP 203"], rows,
                     [S.th(12), S.th(12), S.th(16), S.th(20), S.th(20), S.th(20), S.th(20), S.th(9), S.th(16)])
        notes = [f"fcu = {a.fcu} N/mm2 (cube), fy = {a.fy_slab} N/mm2, clear cover 20 mm.",
                 "B = bottom mesh (full panel), T = top bars over continuous supports, extended L/4 into each "
                 "panel (verify against ECP 203 detailing).",
                 "Discontinuous edges on beams: top bars not less than 1/2 of the bottom steel, extended L/5 "
                 "(verify against ECP 203).",
                 "Loads: own weight + superimposed dead and live area loads read from the model.",
                 "Panels designed by the ECP 203 coefficient method (two-way) or as one-way strips when r > 2."]
        for k, n in enumerate(notes):
            S.text(f"{k + 1}. {n}", tx, yb - S.th(6) - k * S.th(5), 2.5, "ST-TEXT")
        if S.fits():
            break
    return S, N


def draw_flat_story(Sheet, template, M, fl, a, path, short):
    st = fl["story"]
    beams, walls, cols, slabs = story_geometry(M, st)
    xs, ys = fl["xs"], fl["ys"]
    x0, y0 = xs[0], ys[0]
    R = fl["results"]
    for N in (50, 75, 100, 125, 150, 200, 250):
        S = Sheet(template, N)
        W, H, P = _plan_base(S, M, st, beams, walls, cols, xs, ys, x0, y0)
        for pz in R.get("punching", []):
            X, Y = (xs[pz["i"]] - x0) * 1000, (ys[pz["j"]] - y0) * 1000
            S.text(f"{pz['ratio']:.2f}" + ("  FAIL" if pz["ratio"] > 1 else ""), X + S.th(4), Y - S.th(5),
                   2.5 if pz["ratio"] > 1 else 2.0, "ST-TEXT")
        # strip widths: column strip boundaries drawn as thin lines on GN-NPLT? keep as text only
        S.text(f"FLAT SLAB REINFORCEMENT - {st}  (h = {fl['h']} mm)", W / 2, -1500 - S.th(16), 5, "ST-TEXT", "CENTER")
        S.text(f"Scale 1:{N}.  Numbers at columns = punching ratio qup/qcup", W / 2, -1500 - S.th(22), 3, "ST-TEXT",
               "CENTER")
        tx = W + 1500 + S.th(20)
        rows = []
        for s_ in R.get("strips", []):
            sec = {"وش يسار": "left support", "موجب": "span", "وش يمين": "right support"}.get(s_["section"], s_["section"])
            rows.append([s_["frame"], str(s_["span"] + 1), sec, s_["layer"], short(s_["column_strip"] or ""),
                         short(s_["middle_strip"] or "") or "-", f"{s_['M_kNm']:.0f}"])
        S.text("STRIP REINFORCEMENT (per metre width)", tx, H + 1500, 4, "ST-TEXT")
        yb = S.table(tx, H + 1500 - S.th(3), ["Frame", "Span", "Section", "Layer", "Column strip", "Middle strip",
                                              "M kN.m"], rows,
                     [S.th(14), S.th(10), S.th(26), S.th(14), S.th(22), S.th(22), S.th(14)], h=2.0)
        notes = [f"fcu = {a.fcu} N/mm2, fy = {a.fy_slab} N/mm2, cover 20 mm; X layer outer, Y layer inner.",
                 "Equivalent frame method with live-load patterns; column/middle strip split per ECP 203.",
                 "Frame X-k runs along grid line k in X; column strip = half the smaller panel width each side.",
                 f"Max punching ratio = {R.get('max_punching_ratio', 0):.2f} (must be <= 1.00)."]
        for k, n in enumerate(notes):
            S.text(f"{k + 1}. {n}", tx, yb - S.th(6) - k * S.th(5), 2.5, "ST-TEXT")
        if S.fits():
            break
    return S, N


def draw_walls(Sheet, template, wtypes, a, short, bars_per_m):
    for N in (10, 15, 20, 25, 30, 40):
        S = Sheet(template, N)
        x = 0
        for name, lst in wtypes:
            w = lst[0]
            t = w["t"]
            Lw = 1000  # one metre strip in plan
            nv, dv = bars_per_m(w["vert"])
            nh, dh = bars_per_m(w["hor"])
            cv = 25
            S.text(name, x + Lw / 2, t + S.th(14), 4, "ST-TEXT", "CENTER")
            S.rect(x, 0, Lw, t, "ST-WALL")
            for face in (cv + (dh or 8) + (dv or 10) / 2, t - cv - (dh or 8) - (dv or 10) / 2):
                if nv:
                    sp = 1000 / nv
                    xx = x + sp / 2
                    while xx < x + Lw:
                        S.circle((xx, face), (dv or 10) / 2, "ST-RFT", fill=True)
                        xx += sp
            for yy in (cv + (dh or 8) / 2, t - cv - (dh or 8) / 2):
                S.line((x, yy), (x + Lw, yy), "ST-RFT")
            S.dim((x + Lw, 0), (x + Lw, t), S.th(4))
            S.dim((x, t), (x + Lw, t), S.th(4))
            S.text(f"Vert. {short(w['vert'])} each face", x + Lw / 2, -S.th(6), 2.5, "ST-TEXT", "CENTER")
            S.text(f"Hor. {short(w['hor'])} each face", x + Lw / 2, -S.th(11), 2.5, "ST-TEXT", "CENTER")
            x += Lw + S.th(45)
        S.text("WALL TYPES (plan section, 1 m strip)", 0, max(l[0]["t"] for _, l in wtypes) + S.th(26), 5, "ST-TEXT")
        rows = []
        for name, lst in wtypes:
            w = lst[0]
            labs = ", ".join(sorted({f"{i['pier']}@{i['story']}" for i in lst}))
            rows.append([name, str(w["t"]), short(w["vert"]), short(w["hor"]), labs if len(labs) < 60 else labs[:57] + "...",
                         "OK" if all(i["ok"] for i in lst) else "CHECK"])
        yb = S.table(0, -S.th(25), ["Type", "t mm", "Vertical / face", "Horizontal / face", "Piers", "ECP 203"], rows,
                     [S.th(12), S.th(12), S.th(30), S.th(32), S.th(80), S.th(16)])
        notes = [f"fcu = {a.fcu} N/mm2, fy = {a.fy} N/mm2, cover 25 mm, horizontal bars outside vertical bars.",
                 "Pu per metre = max compression from ETABS Pier Forces / pier length; out-of-plane moment = 0 "
                 "unless given.",
                 "Boundary elements, openings, lintels and in-plane shear (shear walls) are not covered - check "
                 "with ETABS shear-wall design / ECP 203."]
        for k, n in enumerate(notes):
            S.text(f"{k + 1}. {n}", 0, yb - S.th(6) - k * S.th(5), 2.5, "ST-TEXT")
        if S.fits():
            break
    return S, N
